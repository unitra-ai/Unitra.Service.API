"""Fixtures for integration tests.

Integration tests use real external services. Required environment variables:
- MODAL_TOKEN_ID: Modal API token ID
- MODAL_TOKEN_SECRET: Modal API token secret
- ML_SERVICE_URL: (optional) Override Modal service URL
"""

import os

import pytest

# Skip all tests in this directory if Modal credentials are not available
pytestmark = pytest.mark.integration


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external services)",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (may take >10s)",
    )


@pytest.fixture(scope="session")
def modal_available() -> bool:
    """Check if Modal credentials are available."""
    token_id = os.getenv("MODAL_TOKEN_ID")
    token_secret = os.getenv("MODAL_TOKEN_SECRET")
    return bool(token_id and token_secret)


@pytest.fixture(scope="session")
def skip_if_no_modal(modal_available: bool):
    """Skip test if Modal is not available."""
    if not modal_available:
        pytest.skip("Modal credentials not available (set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET)")


@pytest.fixture(scope="session")
def modal_service_url() -> str:
    """Get Modal MT service URL."""
    return os.getenv(
        "ML_SERVICE_URL",
        "https://nikmomo--unitra-mt-translate.modal.run",
    )


@pytest.fixture(scope="session")
def modal_health_url() -> str:
    """Get Modal MT health check URL."""
    return os.getenv(
        "ML_HEALTH_URL",
        "https://nikmomo--unitra-mt-health.modal.run",
    )
