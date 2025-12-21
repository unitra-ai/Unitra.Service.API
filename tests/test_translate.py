"""Tests for translation endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_translate_returns_501(async_client: AsyncClient) -> None:
    """Test translate endpoint returns 501 (not implemented)."""
    response = await async_client.post(
        "/api/v1/translate",
        json={
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "zh",
        },
    )
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_list_languages(async_client: AsyncClient) -> None:
    """Test list languages endpoint returns language list."""
    response = await async_client.get("/api/v1/languages")
    assert response.status_code == 200

    data = response.json()
    assert "languages" in data
    assert len(data["languages"]) > 0

    # Check language structure
    lang = data["languages"][0]
    assert "code" in lang
    assert "name" in lang
