# TODO - Future Improvements

## High Priority

### Enable Rate Limiting Middleware

**Status**: Ready to implement, waiting for production Redis configuration

**Current State**:
- ✅ `RateLimitMiddleware` fully implemented in `app/core/middleware.py`
- ✅ Comprehensive test suite exists in `tests/test_rate_limit_middleware.py`
- ✅ All tests passing
- ❌ Not enabled in `app/main.py`

**Implementation**:
To enable, add the following to `app/main.py` after line 87:

```python
# Rate limiting middleware (requires Redis)
from app.core.middleware import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

**Prerequisites**:
1. Verify Redis is available and configured in production
2. Test rate limiting behavior with actual traffic patterns
3. Configure rate limit thresholds per tier if needed

**Configuration**:
- Skipped paths: `/api/health`, `/api/health/live`, `/api/health/ready`, `/api/version`, `/api/docs`, `/api/openapi.json`
- Rate limits defined in `app/core/limits.py`:
  - FREE: 60 requests/minute
  - BASIC: 120 requests/minute
  - PRO: 300 requests/minute
  - ENTERPRISE: 1000 requests/minute

**Testing**:
Before enabling in production:
1. Run load tests with various tier levels
2. Verify Redis connection pooling is optimized
3. Monitor Redis memory usage under load
4. Test rate limit header responses (`X-RateLimit-*`)

**References**:
- Implementation: `app/core/middleware.py:74-170`
- Tests: `tests/test_rate_limit_middleware.py`
- Audit recommendation: AUDIT_REPORT.md line 505

---

## Code Quality (Optional)

### MyPy Type Errors

**Status**: 25 remaining type errors (reduced from 31)

**Current State**:
- Most errors are related to third-party library type stubs (Redis, Starlette)
- Non-blocking, does not affect runtime behavior
- Can be resolved with `# type: ignore` comments or additional type stubs

**Remaining Errors by File**:
- `app/db/redis.py`: 5 errors (Redis library typing)
- `app/core/middleware.py`: 11 errors (Starlette middleware typing)
- `app/core/exception_handlers.py`: 2 errors (Starlette typing)
- `app/core/security.py`: 2 errors (passlib typing - mostly resolved)
- `app/core/logging.py`: 1 error (structlog typing)
- `app/dependencies.py`: 1 error
- `app/auth/manager.py`: 1 error
- `app/auth/backend.py`: 2 errors (resolved - AsyncGenerator)

**Options**:
1. Add `# type: ignore[specific-error]` comments for known safe cases
2. Install additional type stubs: `types-redis`, custom stubs for Starlette
3. Adjust mypy configuration to be less strict for third-party libraries

**Not recommended**: Disabling strict mode - prefer targeted ignores

---

## Documentation

### API Documentation

- [ ] Add OpenAPI examples to endpoint docstrings
- [ ] Document rate limiting behavior in API docs
- [ ] Add authentication flow diagrams
- [ ] Document tier limits and quota system

### Developer Documentation

- [ ] Add architecture decision records (ADRs)
- [ ] Document Redis key schema in detail
- [ ] Add database migration guide
- [ ] Create contributing guide with code review checklist

---

## Performance

### Database Optimization

- [ ] Add composite indexes for common query patterns
- [ ] Implement database connection pooling optimization
- [ ] Add query performance monitoring
- [ ] Consider read replicas for scaling

### Caching Strategy

- [ ] Implement response caching for read-heavy endpoints
- [ ] Add cache warming for frequently accessed data
- [ ] Implement cache invalidation strategy
- [ ] Monitor cache hit rates

---

## Security

### Additional Security Headers

- [ ] Implement Content Security Policy (CSP)
- [ ] Add security.txt file
- [ ] Implement HSTS headers
- [ ] Add rate limiting per IP address (in addition to per user)

### Audit Logging

- [ ] Implement comprehensive audit log for sensitive operations
- [ ] Add log rotation and archival
- [ ] Implement log analysis and alerting
- [ ] Add compliance reporting

---

## Monitoring & Observability

### Metrics

- [ ] Add Prometheus metrics export
- [ ] Implement custom business metrics
- [ ] Add database query performance metrics
- [ ] Monitor rate limit hit rates per tier

### Tracing

- [ ] Implement distributed tracing (OpenTelemetry)
- [ ] Add request flow visualization
- [ ] Implement error tracking (Sentry integration)

---

*Last updated: 2025-12-23*
*Audit report: AUDIT_REPORT.md*
