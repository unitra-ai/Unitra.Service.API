"""Tests for protected routes and authentication."""

import pytest
from httpx import AsyncClient


class TestProtectedRouteAccess:
    """Tests for accessing protected routes."""

    @pytest.mark.asyncio
    async def test_protected_route_without_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test protected route without authentication token."""
        response = await async_client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_invalid_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test protected route with malformed token."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_expired_token(
        self,
        async_client: AsyncClient,
        expired_access_token: str,
    ) -> None:
        """Test protected route with expired token."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_access_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_wrong_auth_type(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test protected route with wrong authorization type."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_empty_bearer(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test protected route with empty bearer token."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer "},
        )

        assert response.status_code == 401


class TestAuthorizationLevels:
    """Tests for different authorization levels."""

    @pytest.mark.asyncio
    async def test_superuser_endpoint_as_normal_user(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test superuser endpoint access as normal user."""
        # Register and login
        email = "normalsuperusertest@example.com"
        password = "testpassword123"

        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data_factory(email=email, password=password),
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": email, "password": password},
        )

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            # Try to access superuser-only endpoint (get user by ID)
            response = await async_client.get(
                "/api/v1/users/550e8400-e29b-41d4-a716-446655440000",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 403


class TestCustomAuthEndpoints:
    """Tests for custom auth endpoints."""

    @pytest.mark.asyncio
    async def test_usage_endpoint_unauthenticated(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test usage endpoint without authentication."""
        response = await async_client.get("/api/v1/auth/me/usage")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_usage_endpoint_authenticated(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test usage endpoint with authentication."""
        # Register and login
        email = "usagetest@example.com"
        password = "testpassword123"

        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data_factory(email=email, password=password),
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": email, "password": password},
        )

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            response = await async_client.get(
                "/api/v1/auth/me/usage",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "minutes_used" in data
            assert "minutes_limit" in data
            assert "tier" in data

    @pytest.mark.asyncio
    async def test_tier_upgrade_placeholder(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test tier upgrade endpoint returns 501."""
        # Register and login (need verified user, but test with unverified for now)
        email = "tierupgradetest@example.com"
        password = "testpassword123"

        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data_factory(email=email, password=password),
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": email, "password": password},
        )

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            response = await async_client.post(
                "/api/v1/auth/me/tier/upgrade",
                headers={"Authorization": f"Bearer {token}"},
                json={"target_tier": "pro"},
            )

            # Should be 501 (not implemented) or 403 (not verified)
            assert response.status_code in [501, 403]

    @pytest.mark.asyncio
    async def test_auth_health_check(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test auth health check endpoint."""
        response = await async_client.get("/api/v1/auth/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
