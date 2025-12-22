# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial FastAPI project setup with Poetry (W1-S01)
- Database schema with SQLAlchemy models: User, Subscription, UsageLog, RefreshToken (W1-S02)
- Redis schema for usage tracking, rate limiting, and token blacklist (W1-S02)
- Tier-based limits configuration (FREE, BASIC, PRO, ENTERPRISE) (W1-S02)
- API Gateway core with exception handlers and middleware (W1-S03)
- 15+ specific exception types for authentication, authorization, validation (W1-S03)
- Common response schemas (SuccessResponse, ErrorResponse, PaginatedResponse) (W1-S03)
- CurrentUserId and OptionalUserId dependencies (W1-S03)
- Billing router stub (W1-S03)
- Structured logging with structlog (W1-S04)
- Component-level health checks with latency reporting (W1-S04)
- Kubernetes liveness and readiness probes (W1-S04)
- Version endpoint with commit SHA (W1-S04)
- CI/CD pipeline with GitHub Actions (W1-X01)
- Dokploy deployment configuration (W1-X01)
- Git workflow documentation and PR template (W1-X02)
- Comprehensive test suite with 200 tests covering all components
  - Exception tests (35 tests for all exception classes)
  - Exception handler tests (11 tests)
  - Middleware tests (15 tests for logging and rate limiting)
  - Dependency tests (20 tests for JWT auth)
  - Schema tests (30 tests for Pydantic validation)
  - Integration tests (30 tests for API endpoints)
  - Logging tests (25 tests for structlog configuration)
- Enhanced test fixtures in conftest.py (auth tokens, mock DB/Redis, async client)
- FastAPI-Users authentication integration
  - User model with UUID, tier, usage tracking, login tracking
  - JWT authentication with custom claims (tier, minutes_remaining)
  - UserManager with lifecycle hooks (register, login, password reset, verification)
  - Auth routers: register, login, logout, forgot-password, reset-password, verify
  - User management: /users/me, /users/{id} (superuser only)
  - Custom endpoints: /auth/me/usage, /auth/me/tier/upgrade (placeholder), /auth/health
  - Comprehensive auth tests (50+ tests covering all auth flows)

### Changed

- Middleware updated to use structlog with correlation ID binding (W1-S04)

### Fixed

- Health check endpoints work when dependencies unavailable (W1-S04)

## [0.1.0] - TBD

### Added

- Initial beta release
- User authentication with JWT
- Translation API endpoints
- Usage tracking and quotas
- Stripe billing integration

---

[Unreleased]: https://github.com/unitra-ai/Unitra.Service.API/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/unitra-ai/Unitra.Service.API/releases/tag/v0.1.0
