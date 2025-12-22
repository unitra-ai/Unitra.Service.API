"""Tests for UserManager lifecycle hooks."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from app.auth.manager import UserManager
from app.auth.models import User, UserTier, TIER_LIMITS


class TestUserManagerHooks:
    """Tests for UserManager lifecycle hooks."""

    @pytest.fixture
    def user_db(self) -> AsyncMock:
        """Create mock user database."""
        return AsyncMock()

    @pytest.fixture
    def user_manager(self, user_db: AsyncMock) -> UserManager:
        """Create UserManager instance."""
        return UserManager(user_db)

    @pytest.fixture
    def mock_user(self) -> MagicMock:
        """Create mock user."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.tier = UserTier.FREE.value
        user.translation_minutes_limit = 60
        user.translation_minutes_used = 0
        user.login_count = 0
        user.last_login_at = None
        user.stripe_subscription_id = None
        return user

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create mock request."""
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request


class TestOnAfterRegister(TestUserManagerHooks):
    """Tests for on_after_register hook."""

    @pytest.mark.asyncio
    async def test_sets_initial_quota(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test registration sets initial quota based on tier."""
        mock_user.tier = UserTier.FREE.value

        await user_manager.on_after_register(mock_user)

        assert mock_user.translation_minutes_limit == TIER_LIMITS[UserTier.FREE]["minutes"]

    @pytest.mark.asyncio
    async def test_sets_quota_for_pro_tier(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test registration sets correct quota for PRO tier."""
        mock_user.tier = UserTier.PRO.value

        await user_manager.on_after_register(mock_user)

        assert mock_user.translation_minutes_limit == TIER_LIMITS[UserTier.PRO]["minutes"]

    @pytest.mark.asyncio
    async def test_logs_registration(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test registration logs event."""
        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_register(mock_user)

            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "user_registered"


class TestOnAfterLogin(TestUserManagerHooks):
    """Tests for on_after_login hook."""

    @pytest.mark.asyncio
    async def test_updates_last_login(
        self,
        user_manager: UserManager,
        mock_user: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Test login updates last_login_at."""
        await user_manager.on_after_login(mock_user, mock_request)

        assert mock_user.last_login_at is not None

    @pytest.mark.asyncio
    async def test_increments_login_count(
        self,
        user_manager: UserManager,
        mock_user: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Test login increments login_count."""
        mock_user.login_count = 5

        await user_manager.on_after_login(mock_user, mock_request)

        assert mock_user.login_count == 6

    @pytest.mark.asyncio
    async def test_uses_forwarded_ip(
        self,
        user_manager: UserManager,
        mock_user: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Test login uses X-Forwarded-For header."""
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}

        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_login(mock_user, mock_request)

            call_args = mock_logger.info.call_args
            assert call_args[1]["ip_address"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_uses_client_host_when_no_forwarded(
        self,
        user_manager: UserManager,
        mock_user: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Test login uses client host when no forwarded header."""
        mock_request.headers = {}
        mock_request.client.host = "10.0.0.5"

        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_login(mock_user, mock_request)

            call_args = mock_logger.info.call_args
            assert call_args[1]["ip_address"] == "10.0.0.5"

    @pytest.mark.asyncio
    async def test_handles_no_request(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test login handles None request."""
        await user_manager.on_after_login(mock_user, None)

        assert mock_user.login_count == 1


class TestOnAfterForgotPassword(TestUserManagerHooks):
    """Tests for on_after_forgot_password hook."""

    @pytest.mark.asyncio
    async def test_logs_password_reset_request(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test forgot password logs request."""
        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_forgot_password(
                mock_user, "reset-token-123"
            )

            # Check info log
            info_calls = [c for c in mock_logger.info.call_args_list]
            assert any("password_reset_requested" in str(c) for c in info_calls)

            # Check warning log with token
            warning_calls = [c for c in mock_logger.warning.call_args_list]
            assert any("password_reset_token_placeholder" in str(c) for c in warning_calls)


class TestOnAfterResetPassword(TestUserManagerHooks):
    """Tests for on_after_reset_password hook."""

    @pytest.mark.asyncio
    async def test_logs_password_reset_completion(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test reset password logs completion."""
        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_reset_password(mock_user)

            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "password_reset_completed"


class TestOnAfterRequestVerify(TestUserManagerHooks):
    """Tests for on_after_request_verify hook."""

    @pytest.mark.asyncio
    async def test_logs_verification_request(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test request verify logs event."""
        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_request_verify(
                mock_user, "verify-token-123"
            )

            info_calls = [c for c in mock_logger.info.call_args_list]
            assert any("verification_requested" in str(c) for c in info_calls)

            warning_calls = [c for c in mock_logger.warning.call_args_list]
            assert any("verification_token_placeholder" in str(c) for c in warning_calls)


class TestOnAfterVerify(TestUserManagerHooks):
    """Tests for on_after_verify hook."""

    @pytest.mark.asyncio
    async def test_logs_verification_success(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test verify logs success."""
        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_verify(mock_user)

            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "user_verified"


class TestOnBeforeDelete(TestUserManagerHooks):
    """Tests for on_before_delete hook."""

    @pytest.mark.asyncio
    async def test_logs_deletion_request(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test delete logs request."""
        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_before_delete(mock_user)

            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "user_deletion_requested"

    @pytest.mark.asyncio
    async def test_logs_subscription_cancellation_placeholder(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test delete logs subscription cancellation placeholder."""
        mock_user.stripe_subscription_id = "sub_123"

        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_before_delete(mock_user)

            debug_calls = [c for c in mock_logger.debug.call_args_list]
            assert any(
                "stripe_subscription_cancellation_placeholder" in str(c)
                for c in debug_calls
            )


class TestOnAfterDelete(TestUserManagerHooks):
    """Tests for on_after_delete hook."""

    @pytest.mark.asyncio
    async def test_logs_deletion_completion(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test delete logs completion."""
        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_delete(mock_user)

            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "user_deleted"


class TestOnAfterUpdate(TestUserManagerHooks):
    """Tests for on_after_update hook."""

    @pytest.mark.asyncio
    async def test_logs_update(
        self, user_manager: UserManager, mock_user: MagicMock
    ) -> None:
        """Test update logs event."""
        update_dict = {"email": "new@example.com", "tier": "pro"}

        with patch("app.auth.manager.logger") as mock_logger:
            await user_manager.on_after_update(mock_user, update_dict)

            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "user_updated"
            assert set(call_args[1]["updated_fields"]) == {"email", "tier"}
