"""Pytest plugin fixtures for jev-judge."""

import os
import pytest
from jev_judge import Judge


def get_default_judge() -> Judge:
    """Instantiate a Judge instance configured for testing."""
    has_key = bool(os.environ.get("TYPESAFE_API_KEY"))
    mock_env = os.environ.get("JEV_MOCK")
    force_mock = (mock_env.lower() in ("1", "true", "yes")) if mock_env is not None else (not has_key)
    return Judge(force_mock=force_mock)


@pytest.fixture
def jev_judge():
    """Pytest fixture providing a preconfigured Judge instance.

    If TYPESAFE_API_KEY is not configured or JEV_MOCK is set, gracefully
    defaults to mock mode so test suites execute deterministically in CI/CD.
    """
    return get_default_judge()


