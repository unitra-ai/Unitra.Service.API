# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload --port 8000

# Run tests
poetry run pytest                              # All tests
poetry run pytest tests/test_health.py -v      # Single file
poetry run pytest -k "test_health_check" -v    # Single test by name
poetry run pytest --cov=app --cov-report=html  # With coverage

# Code quality
poetry run black app/ tests/                   # Format
poetry run ruff check app/ tests/ --fix        # Lint
poetry run mypy app/                           # Type check

# Database migrations
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
poetry run alembic downgrade -1
```

## Architecture Overview

### Request Flow
```
Request → RequestLoggingMiddleware (correlation ID, timing)
        → CORS Middleware
        → Exception Handlers (AppException → JSON response)
        → Router → Endpoint → Dependencies → Response
```

### Authentication (FastAPI-Users)
Authentication is handled by FastAPI-Users (`app/auth/`):
- **User Model**: `app/auth/models.py` - UUID-based, with tier, usage tracking, login tracking
- **Auth Backend**: `app/auth/backend.py` - JWT with custom claims (tier, minutes_remaining)
- **UserManager**: `app/auth/manager.py` - Lifecycle hooks for register, login, password reset, verification

**Auth Dependencies** (from `app/auth/backend.py`):
- `current_user` - Active user required
- `current_verified_user` - Active + verified user required
- `current_superuser` - Superuser required
- `optional_current_user` - Returns None if not authenticated

**Auth Endpoints** (`/api/v1/auth/`):
- `POST /jwt/login` - Login and get JWT
- `POST /register` - User registration
- `POST /forgot-password`, `POST /reset-password` - Password reset flow
- `POST /request-verify-token`, `POST /verify` - Email verification flow
- `GET /me/usage` - Usage statistics
- `GET /health` - Auth system health check

**User Endpoints** (`/api/v1/users/`):
- `GET /me`, `PATCH /me` - Current user profile
- `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` - Superuser only

### Dependency Injection Pattern
Endpoints use FastAPI's `Annotated` type aliases for clean dependency injection:
- `CurrentUserId` - Requires valid JWT, returns user ID string (legacy)
- `OptionalUserId` - Returns user ID or None (legacy)
- `current_user` - FastAPI-Users: Active user required
- `current_verified_user` - FastAPI-Users: Verified user required
- `DbSessionDep` - Async SQLAlchemy session
- `RedisDep` - Redis client instance
- `SettingsDep` - Application settings

### Exception Hierarchy
All custom exceptions inherit from `AppException` which maps to HTTP responses:
- `AuthenticationError` (401) → `TokenExpiredError`, `TokenInvalidError`
- `AuthorizationError` (403) → `InsufficientTierError`, `AccountInactiveError`
- `NotFoundError` (404), `ResourceConflictError` (409)
- `ValidationError` (422) → `InvalidLanguageError`
- `RateLimitError` (429) → `UsageLimitExceededError`
- `ExternalServiceError` (502) → `MLServiceError`, `StripeServiceError`

### Redis Key Schema
```
usage:{user_id}:{week_key}      # Weekly token count (TTL: 8 days)
ratelimit:{user_id}:{endpoint}  # Request counter (TTL: 60s)
blacklist:{token_jti}           # Revoked JWT (TTL: token expiry)
session:{user_id}               # User session HASH (TTL: 24h)
```

### Tier System
Users have tiers (FREE, BASIC, PRO, ENTERPRISE) with limits defined in `app/core/limits.py`:
- `tokens_per_week` - Translation quota
- `requests_per_minute` - Rate limit
- `cloud_mt_allowed` - Access to cloud translation
- `priority_support` - Support tier

### JWT Token Structure
Tokens use `data={"sub": user_id}` format with `type` claim ("access" or "refresh"):
```python
create_access_token(data={"sub": "user-123"})
create_refresh_token(data={"sub": "user-123"})
```

## Key Patterns

### Creating New Endpoints
```python
from app.dependencies import CurrentUserId, DbSessionDep

@router.get("/example")
async def example(
    user_id: CurrentUserId,      # Requires auth
    db: DbSessionDep,            # Database session
) -> dict:
    ...
```

### Raising Errors
```python
from app.core.exceptions import NotFoundError, InsufficientTierError

raise NotFoundError(resource="User", identifier=user_id)
raise InsufficientTierError(required_tier="PRO")
```

### Structured Logging
```python
import structlog
logger = structlog.get_logger("app.module")
logger.info("event_name", user_id=user_id, action="translate")
```

## Configuration
Settings loaded from environment via pydantic-settings (`app/config.py`). Key variables:
- `DATABASE_URL` - PostgreSQL async URL
- `REDIS_URL` - Redis connection
- `SECRET_KEY` - JWT signing key
- `ENVIRONMENT` - development/staging/production
- `DEBUG` - Enables OpenAPI docs at `/api/docs`
