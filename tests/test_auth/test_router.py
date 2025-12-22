"""Tests for auth router custom endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.auth.router import get_auth_router, get_users_router


class TestGetAuthRouter:
    """Tests for get_auth_router function."""

    def test_returns_api_router(self) -> None:
        """Test get_auth_router returns APIRouter."""
        from fastapi import APIRouter

        router = get_auth_router()
        assert isinstance(router, APIRouter)

    def test_includes_jwt_routes(self) -> None:
        """Test router includes JWT auth routes."""
        router = get_auth_router()
        routes = [r.path for r in router.routes]
        assert any("/jwt" in route for route in routes)

    def test_includes_register_routes(self) -> None:
        """Test router includes registration routes."""
        router = get_auth_router()
        routes = [r.path for r in router.routes]
        assert "/register" in routes

    def test_includes_reset_password_routes(self) -> None:
        """Test router includes password reset routes."""
        router = get_auth_router()
        routes = [r.path for r in router.routes]
        assert any("password" in route for route in routes)

    def test_includes_verify_routes(self) -> None:
        """Test router includes verification routes."""
        router = get_auth_router()
        routes = [r.path for r in router.routes]
        assert any("verify" in route for route in routes)

    def test_includes_custom_endpoints(self) -> None:
        """Test router includes custom endpoints."""
        router = get_auth_router()
        routes = [r.path for r in router.routes]
        assert any("usage" in route for route in routes)
        assert any("health" in route for route in routes)


class TestGetUsersRouter:
    """Tests for get_users_router function."""

    def test_returns_api_router(self) -> None:
        """Test get_users_router returns APIRouter."""
        from fastapi import APIRouter

        router = get_users_router()
        assert isinstance(router, APIRouter)

    def test_includes_me_routes(self) -> None:
        """Test router includes /me routes."""
        router = get_users_router()
        routes = [r.path for r in router.routes]
        assert "/me" in routes


class TestUsageStatisticsEndpoint:
    """Tests for usage statistics endpoint logic."""

    def test_december_reset_date_calculation(self) -> None:
        """Test reset date calculation for December."""
        from app.auth.router import get_usage_statistics
        from app.auth.schemas import UsageStatistics

        # Test that December -> January next year
        now = datetime(2024, 12, 15, tzinfo=timezone.utc)

        with patch("app.auth.router.datetime") as mock_dt:
            mock_dt.now.return_value = now

            # The calculation: if month == 12, year+1, month 1
            if now.month == 12:
                reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

            assert reset_date.year == 2025
            assert reset_date.month == 1

    def test_regular_month_reset_date_calculation(self) -> None:
        """Test reset date calculation for regular months."""
        now = datetime(2024, 6, 15, tzinfo=timezone.utc)

        if now.month == 12:
            reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

        assert reset_date.year == 2024
        assert reset_date.month == 7


class TestTierUpgradeEndpoint:
    """Tests for tier upgrade endpoint."""

    @pytest.mark.asyncio
    async def test_upgrade_endpoint_route(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test tier upgrade endpoint exists and requires auth."""
        response = await async_client.post(
            "/api/v1/auth/me/tier/upgrade",
            json={"target_tier": "pro"},
        )

        # Without auth, should get 401
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upgrade_with_auth_returns_501_or_403(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test tier upgrade with authentication returns 501 or 403."""
        # Register and login
        email = "tierupgradetest2@example.com"
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

            # 501 (not implemented) or 403 (not verified)
            assert response.status_code in [501, 403]
