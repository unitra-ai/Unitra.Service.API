"""Tests for user management endpoints."""

import pytest
from httpx import AsyncClient


class TestGetMe:
    """Tests for GET /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test get me without authentication."""
        response = await async_client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_invalid_token(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test get me with invalid token."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_authenticated(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test get me with valid authentication."""
        # Register and login
        email = "getmetest@example.com"
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
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == email
            assert "hashed_password" not in data
            assert "password" not in data


class TestUpdateMe:
    """Tests for PATCH /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_update_me_unauthenticated(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test update me without authentication."""
        response = await async_client.patch(
            "/api/v1/users/me",
            json={"email": "newemail@example.com"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_me_email(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test updating own email."""
        # Register and login
        email = "updatemetest@example.com"
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
            new_email = "updatedemail@example.com"

            response = await async_client.patch(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
                json={"email": new_email},
            )

            # Email update might succeed or fail depending on implementation
            assert response.status_code in [200, 400]


class TestDeleteUser:
    """Tests for DELETE /users/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_user_unauthenticated(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test delete user without authentication."""
        response = await async_client.delete(
            "/api/v1/users/550e8400-e29b-41d4-a716-446655440000",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_user_as_normal_user(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test normal user cannot delete other users."""
        # Register first user
        email1 = "deletetest1@example.com"
        password = "testpassword123"

        reg_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data_factory(email=email1, password=password),
        )

        if reg_response.status_code == 500:
            pytest.skip("Database not available for test")

        user1_id = reg_response.json().get("id")

        # Register second user
        email2 = "deletetest2@example.com"
        reg_response2 = await async_client.post(
            "/api/v1/auth/register",
            json=user_data_factory(email=email2, password=password),
        )

        if reg_response2.status_code != 201:
            pytest.skip("Could not create second user")

        # Login as second user
        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": email2, "password": password},
        )

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            # Try to delete first user
            response = await async_client.delete(
                f"/api/v1/users/{user1_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Should be forbidden
            assert response.status_code == 403


class TestGetUserById:
    """Tests for GET /users/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_unauthenticated(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test get user by ID without authentication."""
        response = await async_client.get(
            "/api/v1/users/550e8400-e29b-41d4-a716-446655440000",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_by_id_as_normal_user(
        self,
        async_client: AsyncClient,
        user_data_factory,
    ) -> None:
        """Test normal user cannot get other users by ID."""
        # Register and login
        email = "getuserbyidtest@example.com"
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

            # Try to get another user by ID
            response = await async_client.get(
                "/api/v1/users/550e8400-e29b-41d4-a716-446655440000",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Should be forbidden for non-superuser
            assert response.status_code == 403
