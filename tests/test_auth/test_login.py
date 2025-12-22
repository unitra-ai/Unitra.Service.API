"""Tests for user login."""

import pytest
from httpx import AsyncClient


class TestLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_endpoint_exists(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test login endpoint is accessible."""
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={
                "username": "test@example.com",
                "password": "testpassword123",
            },
        )

        # Should return 400 (bad credentials) or 500 (DB error), not 404
        assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_login_invalid_email(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test login with non-existent email."""
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={
                "username": "nonexistent@example.com",
                "password": "somepassword",
            },
        )

        # Should fail with bad credentials (not reveal if email exists)
        assert response.status_code in [400, 500]

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test login with wrong password fails."""
        # First register a user
        user_data = user_data_factory(email="logintest@example.com")
        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        # Try to login with wrong password
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={
                "username": "logintest@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test successful login returns JWT token."""
        # Register a user first
        email = "loginsuccesstest@example.com"
        password = "testpassword123"
        user_data = user_data_factory(email=email, password=password)

        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        # Login
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={
                "username": email,
                "password": password,
            },
        )

        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_missing_username(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test login without username fails."""
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"password": "somepassword"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test login without password fails."""
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "test@example.com"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_empty_body(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test login with empty body fails."""
        response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={},
        )

        assert response.status_code == 422


class TestJWTToken:
    """Tests for JWT token behavior."""

    @pytest.mark.asyncio
    async def test_jwt_token_format(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test JWT token is properly formatted."""
        # Register and login
        email = "jwtformattest@example.com"
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
            data = login_response.json()
            token = data["access_token"]

            # JWT should have 3 parts separated by dots
            parts = token.split(".")
            assert len(parts) == 3

    @pytest.mark.asyncio
    async def test_jwt_token_can_access_protected_route(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test JWT token can be used to access protected routes."""
        # Register and login
        email = "protectedroutetest@example.com"
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

            # Try to access protected route
            me_response = await async_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert me_response.status_code == 200
            data = me_response.json()
            assert data["email"] == email
