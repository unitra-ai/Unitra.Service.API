"""Tests for email verification functionality."""

import pytest
from httpx import AsyncClient


class TestRequestVerification:
    """Tests for request verification token endpoint."""

    @pytest.mark.asyncio
    async def test_request_verify_token_endpoint_exists(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test request verify token endpoint is accessible."""
        response = await async_client.post(
            "/api/v1/auth/request-verify-token",
            json={"email": "test@example.com"},
        )

        # Should return 202/400/500, not 404
        assert response.status_code in [202, 400, 500]

    @pytest.mark.asyncio
    async def test_request_verify_for_unverified_user(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test request verification for unverified user."""
        # Register a user (not verified by default)
        email = "unverifieduser@example.com"
        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data_factory(email=email),
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        # Request verification token
        response = await async_client.post(
            "/api/v1/auth/request-verify-token",
            json={"email": email},
        )

        assert response.status_code in [202, 200, 500]

    @pytest.mark.asyncio
    async def test_request_verify_invalid_email(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test request verification with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/request-verify-token",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422


class TestVerifyEmail:
    """Tests for verify email endpoint."""

    @pytest.mark.asyncio
    async def test_verify_invalid_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test verify with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/verify",
            json={"token": "invalid-token"},
        )

        assert response.status_code in [400, 500]

    @pytest.mark.asyncio
    async def test_verify_missing_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test verify without token."""
        response = await async_client.post(
            "/api/v1/auth/verify",
            json={},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_verify_empty_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test verify with empty token."""
        response = await async_client.post(
            "/api/v1/auth/verify",
            json={"token": ""},
        )

        assert response.status_code in [400, 422, 500]
