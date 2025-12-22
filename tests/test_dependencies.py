"""Tests for dependency injection."""

from datetime import timedelta
from unittest.mock import patch

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, create_refresh_token
from app.dependencies import get_current_user_id, get_optional_user_id


# =============================================================================
# get_current_user_id Tests
# =============================================================================


class TestGetCurrentUserId:
    """Tests for get_current_user_id dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_id_from_valid_token(self) -> None:
        """Test extracting user ID from valid token."""
        token = create_access_token(data={"sub": "user-123"})
        authorization = f"Bearer {token}"

        user_id = await get_current_user_id(authorization=authorization)

        assert user_id == "user-123"

    @pytest.mark.asyncio
    async def test_raises_error_when_no_authorization(self) -> None:
        """Test error when authorization header is missing."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user_id(authorization=None)

        assert "Missing authorization header" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_format(self) -> None:
        """Test error when authorization format is invalid."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user_id(authorization="InvalidFormat token")

        assert "Invalid authorization header format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_error_for_basic_auth(self) -> None:
        """Test error when Basic auth is used instead of Bearer."""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user_id(authorization="Basic dXNlcjpwYXNz")

        assert "Invalid authorization header format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_error_for_expired_token(self) -> None:
        """Test error when token is expired."""
        token = create_access_token(
            data={"sub": "user-123"},
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        authorization = f"Bearer {token}"

        with pytest.raises(AuthenticationError):
            await get_current_user_id(authorization=authorization)

    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_token(self) -> None:
        """Test error when token is malformed."""
        authorization = "Bearer invalid.token.here"

        with pytest.raises(AuthenticationError):
            await get_current_user_id(authorization=authorization)

    @pytest.mark.asyncio
    async def test_raises_error_for_empty_bearer(self) -> None:
        """Test error when Bearer token is empty."""
        authorization = "Bearer "

        with pytest.raises(AuthenticationError):
            await get_current_user_id(authorization=authorization)

    @pytest.mark.asyncio
    async def test_handles_token_with_additional_claims(self) -> None:
        """Test token with additional claims is processed correctly."""
        token = create_access_token(
            data={"sub": "user-456", "email": "test@example.com", "role": "admin"},
        )
        authorization = f"Bearer {token}"

        user_id = await get_current_user_id(authorization=authorization)

        assert user_id == "user-456"


# =============================================================================
# get_optional_user_id Tests
# =============================================================================


class TestGetOptionalUserId:
    """Tests for get_optional_user_id dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_id_from_valid_token(self) -> None:
        """Test extracting user ID from valid token."""
        token = create_access_token(data={"sub": "user-789"})
        authorization = f"Bearer {token}"

        user_id = await get_optional_user_id(authorization=authorization)

        assert user_id == "user-789"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_authorization(self) -> None:
        """Test returns None when authorization is missing."""
        user_id = await get_optional_user_id(authorization=None)

        assert user_id is None

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_token(self) -> None:
        """Test returns None when token is invalid."""
        authorization = "Bearer invalid.token"

        user_id = await get_optional_user_id(authorization=authorization)

        assert user_id is None

    @pytest.mark.asyncio
    async def test_returns_none_for_expired_token(self) -> None:
        """Test returns None when token is expired."""
        token = create_access_token(
            data={"sub": "user-123"},
            expires_delta=timedelta(seconds=-1),
        )
        authorization = f"Bearer {token}"

        user_id = await get_optional_user_id(authorization=authorization)

        assert user_id is None

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_format(self) -> None:
        """Test returns None when authorization format is invalid."""
        authorization = "Basic dXNlcjpwYXNz"

        user_id = await get_optional_user_id(authorization=authorization)

        assert user_id is None

    @pytest.mark.asyncio
    async def test_does_not_raise_exception(self) -> None:
        """Test that invalid auth never raises exception."""
        invalid_authorizations = [
            None,
            "",
            "Bearer",
            "Bearer ",
            "Bearer invalid",
            "Basic auth",
            "malformed",
        ]

        for auth in invalid_authorizations:
            # Should not raise
            result = await get_optional_user_id(authorization=auth)
            assert result is None, f"Expected None for auth: {auth}"


# =============================================================================
# Token Edge Cases
# =============================================================================


class TestTokenEdgeCases:
    """Tests for edge cases in token handling."""

    @pytest.mark.asyncio
    async def test_token_without_subject_claim(self) -> None:
        """Test token without 'sub' claim raises error."""
        # Create a token manually without subject
        from datetime import datetime, timezone

        from jose import jwt

        from app.config import get_settings

        settings = get_settings()
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "access",
            # No 'sub' claim
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        authorization = f"Bearer {token}"

        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user_id(authorization=authorization)

        assert "subject" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_token_with_wrong_type(self) -> None:
        """Test token with wrong type (refresh instead of access)."""
        token = create_refresh_token(data={"sub": "user-123"})
        authorization = f"Bearer {token}"

        # Should raise an error because it's a refresh token, not access
        with pytest.raises(AuthenticationError):
            await get_current_user_id(authorization=authorization)

    @pytest.mark.asyncio
    async def test_very_long_user_id(self) -> None:
        """Test token with very long user ID."""
        long_id = "user-" + "x" * 1000
        token = create_access_token(data={"sub": long_id})
        authorization = f"Bearer {token}"

        user_id = await get_current_user_id(authorization=authorization)

        assert user_id == long_id

    @pytest.mark.asyncio
    async def test_special_characters_in_user_id(self) -> None:
        """Test token with special characters in user ID."""
        special_id = "user_123-abc.def@example"
        token = create_access_token(data={"sub": special_id})
        authorization = f"Bearer {token}"

        user_id = await get_current_user_id(authorization=authorization)

        assert user_id == special_id

    @pytest.mark.asyncio
    async def test_unicode_in_user_id(self) -> None:
        """Test token with unicode characters in user ID."""
        unicode_id = "用户-123"
        token = create_access_token(data={"sub": unicode_id})
        authorization = f"Bearer {token}"

        user_id = await get_current_user_id(authorization=authorization)

        assert user_id == unicode_id


# =============================================================================
# Concurrent Access Tests
# =============================================================================


class TestConcurrentAccess:
    """Tests for concurrent token validation."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_validations(self) -> None:
        """Test multiple tokens can be validated concurrently."""
        import asyncio

        tokens = [
            create_access_token(data={"sub": f"user-{i}"})
            for i in range(10)
        ]

        async def validate_token(token: str, expected_id: str) -> bool:
            auth = f"Bearer {token}"
            user_id = await get_current_user_id(authorization=auth)
            return user_id == expected_id

        tasks = [
            validate_token(token, f"user-{i}")
            for i, token in enumerate(tokens)
        ]

        results = await asyncio.gather(*tasks)

        assert all(results), "All token validations should succeed"
