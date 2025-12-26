"""Batch processor that interfaces with Modal MT service.

Responsibilities:
- Call Modal MT service with batched texts
- Handle retries and errors
- Track processing metrics
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class TranslationError(Exception):
    """Translation service error."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class BatchProcessor:
    """Processes translation batches via Modal MT service.

    Handles communication with the Modal-hosted MADLAD-400 model,
    including retries, error handling, and metrics tracking.
    """

    # Default Modal endpoint (can be overridden via settings)
    DEFAULT_ENDPOINT = "https://nikmomo--unitra-mt-translate.modal.run"

    def __init__(
        self,
        modal_endpoint: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ):
        """Initialize the batch processor.

        Args:
            modal_endpoint: Modal MT service endpoint URL
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        settings = get_settings()
        self.modal_endpoint = (
            modal_endpoint or settings.ml_service_url or self.DEFAULT_ENDPOINT
        ).rstrip("/")
        self.timeout = timeout_seconds
        self.max_retries = max_retries

        self._client: httpx.AsyncClient | None = None

        # Metrics
        self._total_batches = 0
        self._total_requests = 0
        self._total_tokens = 0
        self._total_errors = 0
        self._total_retries = 0
        self._total_process_time_ms = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    async def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[str]:
        """Translate a batch of texts.

        Args:
            texts: List of source texts
            source_lang: ISO 639-1 source language code
            target_lang: ISO 639-1 target language code

        Returns:
            List of translated texts (same order as input)

        Raises:
            TranslationError: If translation fails after retries
        """
        if not texts:
            return []

        client = await self._get_client()
        start_time = time.time()

        # Use batch endpoint if multiple texts, single endpoint otherwise
        if len(texts) == 1:
            payload: dict[str, Any] = {
                "text": texts[0],
                "source_lang": source_lang,
                "target_lang": target_lang,
            }
        else:
            payload = {
                "texts": texts,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post(
                    self.modal_endpoint,
                    json=payload,
                )
                response.raise_for_status()

                result = response.json()
                process_time_ms = (time.time() - start_time) * 1000

                # Update metrics
                self._total_batches += 1
                self._total_requests += len(texts)
                self._total_tokens += result.get("tokens_used", 0) or result.get(
                    "total_tokens", 0
                )
                self._total_process_time_ms += process_time_ms

                # Extract translations
                if len(texts) == 1:
                    return [result["translation"]]
                else:
                    return result["translations"]

            except httpx.HTTPStatusError as e:
                last_error = e
                self._total_errors += 1

                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    logger.error(
                        "translation_client_error",
                        status_code=e.response.status_code,
                        response=e.response.text[:200],
                    )
                    raise TranslationError(
                        f"Translation failed: {e.response.status_code}",
                        retryable=False,
                    ) from e

                # Retry server errors (5xx)
                if attempt < self.max_retries:
                    self._total_retries += 1
                    wait_time = 0.1 * (2**attempt)  # Exponential backoff
                    logger.warning(
                        "translation_retry",
                        attempt=attempt + 1,
                        status_code=e.response.status_code,
                        wait_time=wait_time,
                    )
                    await asyncio.sleep(wait_time)

            except httpx.RequestError as e:
                last_error = e
                self._total_errors += 1

                if attempt < self.max_retries:
                    self._total_retries += 1
                    wait_time = 0.1 * (2**attempt)
                    logger.warning(
                        "translation_request_error",
                        attempt=attempt + 1,
                        error=str(e),
                        wait_time=wait_time,
                    )
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        logger.error(
            "translation_failed",
            error=str(last_error),
            attempts=self.max_retries + 1,
            batch_size=len(texts),
        )
        raise TranslationError(f"Batch translation failed: {last_error}") from last_error

    async def translate_single(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate a single text.

        Convenience method that wraps translate_batch for single texts.

        Args:
            text: Source text
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text
        """
        results = await self.translate_batch([text], source_lang, target_lang)
        return results[0]

    async def health_check(self) -> dict:
        """Check Modal service health.

        Returns:
            Health status dictionary
        """
        client = await self._get_client()
        health_url = self.modal_endpoint.replace("-translate", "-health")

        try:
            response = await client.get(health_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}

    def get_metrics(self) -> dict:
        """Get processor metrics.

        Returns:
            Dictionary with processor statistics
        """
        avg_process_time = (
            self._total_process_time_ms / self._total_batches
            if self._total_batches > 0
            else 0
        )
        avg_batch_size = (
            self._total_requests / self._total_batches if self._total_batches > 0 else 0
        )

        return {
            "total_batches": self._total_batches,
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_errors": self._total_errors,
            "total_retries": self._total_retries,
            "avg_process_time_ms": round(avg_process_time, 2),
            "avg_batch_size": round(avg_batch_size, 2),
            "error_rate": (
                round(self._total_errors / self._total_batches, 4)
                if self._total_batches > 0
                else 0
            ),
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._total_batches = 0
        self._total_requests = 0
        self._total_tokens = 0
        self._total_errors = 0
        self._total_retries = 0
        self._total_process_time_ms = 0.0

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "BatchProcessor":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()
