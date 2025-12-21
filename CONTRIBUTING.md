# Contributing to Unitra Service API

Thank you for your interest in contributing to Unitra!

## Getting Started

### Prerequisites

- Python 3.10+
- Poetry 1.7+
- Docker & Docker Compose (for local development)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/unitra-ai/Unitra.Service.API.git
   cd Unitra.Service.API
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Install pre-commit hooks:
   ```bash
   poetry run pre-commit install
   ```

4. Start development services:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

5. Run the development server:
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

See [Git Workflow](docs/GIT_WORKFLOW.md) for branch naming conventions.

### 2. Make Changes

- Write code following our style guidelines
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_health.py -v
```

### 4. Check Code Quality

```bash
# Run all pre-commit hooks
poetry run pre-commit run --all-files

# Or run individually:
poetry run black app tests      # Format code
poetry run ruff check app tests # Lint code
poetry run mypy app             # Type check
poetry run bandit -r app -ll    # Security check
```

### 5. Commit Changes

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat(api): add new endpoint for X"
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Maintenance

### 6. Push and Create PR

```bash
git push -u origin feature/your-feature-name
```

Then create a Pull Request on GitHub using the PR template.

## Code Style

- **Formatter**: Black (line length: 100)
- **Linter**: Ruff
- **Type Checker**: MyPy (strict mode)

### Python Guidelines

- Use type hints for all function parameters and return values
- Write docstrings for public functions and classes
- Keep functions focused and small
- Prefer explicit over implicit

### Example

```python
async def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
) -> TranslationResult:
    """Translate text from source to target language.

    Args:
        text: The text to translate.
        source_lang: Source language code (e.g., "en").
        target_lang: Target language code (e.g., "zh").

    Returns:
        TranslationResult with translated text and metadata.

    Raises:
        InvalidLanguageError: If language code is not supported.
        MLServiceError: If translation service is unavailable.
    """
    # Implementation...
```

## Testing

- Write tests for all new features
- Maintain or improve code coverage
- Use pytest fixtures for common setup
- Test both success and error cases

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_health.py       # Health endpoint tests
├── test_auth.py         # Authentication tests
└── test_translate.py    # Translation tests
```

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)
- [ ] No merge conflicts with main

### PR Title

Use conventional commit format:
```
feat(auth): add password reset functionality
fix(api): handle empty translation requests
docs: update API documentation
```

### Review Process

1. At least 1 approval required
2. All CI checks must pass
3. Address all feedback
4. Squash merge to main

## Questions?

- Check existing issues and PRs
- Open a new issue for bugs or feature requests
- Start a discussion for questions

## License

By contributing, you agree that your contributions will be licensed under the project's license.
