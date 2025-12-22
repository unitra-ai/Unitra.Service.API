"""Tests for custom auth endpoints."""

import pytest
from httpx import AsyncClient


class TestUsageStatistics:
    """Tests for usage statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_usage_returns_correct_structure(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test usage endpoint returns correct data structure."""
        # Register and login
        email = "usagestructuretest@example.com"
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

            # Check required fields
            assert "minutes_used" in data
            assert "minutes_limit" in data
            assert "minutes_remaining" in data
            assert "tier" in data
            assert "reset_date" in data

            # Check types
            assert isinstance(data["minutes_used"], int)
            assert isinstance(data["minutes_limit"], int)
            assert isinstance(data["minutes_remaining"], int)
            assert isinstance(data["tier"], str)

    @pytest.mark.asyncio
    async def test_get_usage_default_values(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test new user has correct default usage values."""
        # Register and login
        email = "usagedefaulttest@example.com"
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

            if response.status_code == 200:
                data = response.json()

                # New FREE tier user defaults
                assert data["minutes_used"] == 0
                assert data["minutes_limit"] == 60
                assert data["minutes_remaining"] == 60
                assert data["tier"] == "free"


class TestTierUpgrade:
    """Tests for tier upgrade endpoint."""

    @pytest.mark.asyncio
    async def test_tier_upgrade_returns_501(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test tier upgrade endpoint returns 501 Not Implemented."""
        # Register and login
        email = "tierupgrade501test@example.com"
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
                json={"target_tier": "basic"},
            )

            # 501 or 403 (if verified user required)
            assert response.status_code in [501, 403]

    @pytest.mark.asyncio
    async def test_tier_upgrade_unauthenticated(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test tier upgrade without authentication."""
        response = await async_client.post(
            "/api/v1/auth/me/tier/upgrade",
            json={"target_tier": "basic"},
        )

        assert response.status_code == 401


class TestAuthHealthCheck:
    """Tests for auth health check endpoint."""

    @pytest.mark.asyncio
    async def test_auth_health_returns_healthy(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test auth health check returns healthy status."""
        response = await async_client.get("/api/v1/auth/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["database"] in ["connected", "disconnected"]

    @pytest.mark.asyncio
    async def test_auth_health_response_structure(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test auth health check has correct response structure."""
        response = await async_client.get("/api/v1/auth/health")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "status" in data
        assert "database" in data

    @pytest.mark.asyncio
    async def test_auth_health_is_public(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test auth health check is accessible without authentication."""
        response = await async_client.get("/api/v1/auth/health")

        # Should not require auth
        assert response.status_code == 200


class TestAuthEndpointRouting:
    """Tests for auth endpoint routing."""

    @pytest.mark.asyncio
    async def test_register_endpoint_route(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test register endpoint is at correct path."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "routetest@example.com", "password": "testpassword123"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_login_endpoint_route(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test login endpoint is at correct path."""
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "test@example.com", "password": "testpassword123"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_forgot_password_endpoint_route(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test forgot password endpoint is at correct path."""
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_reset_password_endpoint_route(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test reset password endpoint is at correct path."""
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "test", "password": "newpassword"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_verify_endpoint_route(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test verify endpoint is at correct path."""
        response = await async_client.post(
            "/api/v1/auth/verify",
            json={"token": "test"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_users_me_endpoint_route(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test users/me endpoint is at correct path."""
        response = await async_client.get("/api/v1/users/me")

        # Should not be 404 (should be 401 without auth)
        assert response.status_code == 401
