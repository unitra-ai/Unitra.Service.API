"""Modal MT Service client.

This module provides an HTTP client for calling the Modal-hosted
machine translation service.
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.core.exceptions import MLServiceError

logger = structlog.get_logger(__name__)


@dataclass
class TranslationResult:
    """Result from a translation request."""

    translation: str
    source_lang: str
    target_lang: str
    tokens_used: int
    latency_ms: float
    processing_mode: str = "cloud"


@dataclass
class BatchTranslationResult:
    """Result from a batch translation request."""

    translations: list[str]
    source_lang: str
    target_lang: str
    total_tokens: int
    latency_ms: float
    processing_mode: str = "cloud"


@dataclass
class HealthStatus:
    """Health status of the MT service."""

    status: str
    model_id: str
    model_loaded: bool
    gpu_available: bool
    warm: bool


class MTClient:
    """HTTP client for Modal MT service.

    This client provides async methods for calling the Modal-hosted
    machine translation service.
    """

    # Default Modal web endpoint URL
    DEFAULT_BASE_URL = "https://nikmomo--unitra-mt-translate.modal.run"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
        api_key: str | None = None,
    ):
        """Initialize the MT client.

        Args:
            base_url: Base URL of the Modal web endpoint.
            timeout: Request timeout in seconds.
            api_key: API key for authenticating with the ML service.
        """
        settings = get_settings()
        self.base_url = (base_url or settings.ml_service_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or settings.modal_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "MTClient":
        """Enter async context manager."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client."""
        if self._client is None:
            raise RuntimeError(
                "MTClient must be used as an async context manager: "
                "async with MTClient() as client: ..."
            )
        return self._client

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate a single text.

        Args:
            text: Text to translate (max 512 characters)
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "zh")

        Returns:
            TranslationResult with translation and metadata

        Raises:
            MLServiceError: If translation fails
        """
        try:
            logger.info(
                "translate_request",
                source_lang=source_lang,
                target_lang=target_lang,
                text_length=len(text),
            )

            response = await self.client.post(
                f"{self.base_url}/translate",
                json={
                    "text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                },
            )
            response.raise_for_status()
            data = response.json()

            result = TranslationResult(
                translation=data["translation"],
                source_lang=data["source_lang"],
                target_lang=data["target_lang"],
                tokens_used=data["tokens_used"],
                latency_ms=data["latency_ms"],
                processing_mode=data.get("processing_mode", "cloud"),
            )

            logger.info(
                "translate_success",
                tokens_used=result.tokens_used,
                latency_ms=result.latency_ms,
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "translate_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise MLServiceError(f"Translation failed with status {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("translate_request_error", error=str(e))
            raise MLServiceError(f"Translation request failed: {e}") from e

    async def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> BatchTranslationResult:
        """Translate a batch of texts.

        Args:
            texts: List of texts to translate (max 16 texts, each max 512 chars)
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "zh")

        Returns:
            BatchTranslationResult with translations and metadata

        Raises:
            MLServiceError: If translation fails
        """
        try:
            logger.info(
                "translate_batch_request",
                source_lang=source_lang,
                target_lang=target_lang,
                batch_size=len(texts),
            )

            response = await self.client.post(
                f"{self.base_url}/translate",
                json={
                    "texts": texts,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                },
            )
            response.raise_for_status()
            data = response.json()

            result = BatchTranslationResult(
                translations=data["translations"],
                source_lang=data["source_lang"],
                target_lang=data["target_lang"],
                total_tokens=data["total_tokens"],
                latency_ms=data["latency_ms"],
                processing_mode=data.get("processing_mode", "cloud"),
            )

            logger.info(
                "translate_batch_success",
                total_tokens=result.total_tokens,
                latency_ms=result.latency_ms,
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "translate_batch_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise MLServiceError(
                f"Batch translation failed with status {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error("translate_batch_request_error", error=str(e))
            raise MLServiceError(f"Batch translation request failed: {e}") from e

    async def health_check(self) -> HealthStatus:
        """Check health of the MT service.

        Returns:
            HealthStatus with service status

        Raises:
            MLServiceError: If health check fails
        """
        try:
            # The health endpoint is separate from translate
            health_url = self.base_url.replace("-translate", "-health")
            response = await self.client.get(f"{health_url}/health")
            response.raise_for_status()
            data = response.json()

            return HealthStatus(
                status=data["status"],
                model_id=data["model_id"],
                model_loaded=data["model_loaded"],
                gpu_available=data["gpu_available"],
                warm=data["warm"],
            )

        except httpx.HTTPStatusError as e:
            logger.error("health_check_http_error", status_code=e.response.status_code)
            raise MLServiceError(f"Health check failed with status {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("health_check_request_error", error=str(e))
            raise MLServiceError(f"Health check request failed: {e}") from e


# Global client instance (for connection reuse)
_mt_client: MTClient | None = None


async def get_mt_client() -> AsyncGenerator[MTClient, None]:
    """Get MT client for dependency injection.

    Creates a new client for each request to ensure proper
    connection management.
    """
    async with MTClient() as client:
        yield client
