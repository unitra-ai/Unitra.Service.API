# Unitra Service API

FastAPI backend for Unitra translation platform.

## Quick Start

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Start development server
poetry run uvicorn app.main:app --reload --port 8000
```

## Project Structure

```
app/
├── api/                    # API endpoints
│   ├── router.py          # Main router
│   └── v1/                # V1 endpoints
│       ├── auth.py        # Authentication
│       ├── health.py      # Health check
│       ├── translate.py   # Translation
│       └── usage.py       # Usage tracking
├── core/                   # Core functionality
│   ├── exceptions.py      # Custom exceptions
│   ├── middleware.py      # Custom middleware
│   └── security.py        # JWT & password hashing
├── db/                     # Database
│   ├── base.py            # SQLAlchemy base
│   ├── redis.py           # Redis client
│   └── session.py         # DB session management
├── models/                 # SQLAlchemy models
├── schemas/                # Pydantic schemas
├── services/               # Business logic
├── config.py              # Settings
├── dependencies.py        # DI dependencies
└── main.py                # App factory
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/translate` | Translate text |
| POST | `/api/v1/translate/batch` | Batch translation |
| GET | `/api/v1/languages` | List languages |
| GET | `/api/v1/usage` | Usage statistics |

## Development

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=app --cov-report=html

# Format code
poetry run black app/ tests/
poetry run ruff check app/ tests/ --fix

# Type checking
poetry run mypy app/
```

## Database Migrations

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## Docker

### Development
```bash
cd docker
docker-compose up
```

### Production
```bash
docker build -t unitra-api .
docker run -p 8000:8000 --env-file .env unitra-api
```

## API Documentation

When `DEBUG=true`, API docs are available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json
