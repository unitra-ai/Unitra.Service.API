# Unitra Service API

FastAPI backend for Unitra translation platform.

## Setup

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Start development server
poetry run uvicorn app.main:app --reload --port 8000
```

## API Endpoints

- `GET /health` - Health check
- `POST /v1/translate` - Translate text
- `GET /v1/usage` - Get usage statistics

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black app/
poetry run ruff check app/ --fix

# Type checking
poetry run mypy app/
```

## Docker

```bash
docker build -t unitra-api .
docker run -p 8000:8000 --env-file .env unitra-api
```
