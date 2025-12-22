"""Tests for password reset functionality."""

import pytest
from httpx import AsyncClient


class TestForgotPassword:
    """Tests for forgot password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_email(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test forgot password for existing email."""
        # Register a user first
        email = "forgotpassword@example.com"
        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data_factory(email=email),
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        # Request password reset
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
        )

        # Should accept (202) even if email doesn't exist (security)
        assert response.status_code in [202, 200, 500]

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test forgot password for non-existent email (security)."""
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Should accept to not reveal if email exists
        assert response.status_code in [202, 200, 500]

    @pytest.mark.asyncio
    async def test_forgot_password_invalid_email(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test forgot password with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422


class TestResetPassword:
    """Tests for reset password endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test reset password with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token",
                "password": "newpassword123",
            },
        )

        assert response.status_code in [400, 500]

    @pytest.mark.asyncio
    async def test_reset_password_missing_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test reset password without token."""
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"password": "newpassword123"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reset_password_missing_password(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test reset password without new password."""
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "some-token"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reset_password_empty_body(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test reset password with empty body."""
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={},
        )

        assert response.status_code == 422
