"""Integration tests for external services.

These tests require real external services (Modal, Redis, etc.) and should be
run separately from unit tests. Use pytest markers to control execution:

    # Run only unit tests (fast, no external dependencies)
    pytest -m "not integration"

    # Run only integration tests (requires MODAL_TOKEN_ID, MODAL_TOKEN_SECRET)
    pytest -m integration

    # Run all tests
    pytest
"""
