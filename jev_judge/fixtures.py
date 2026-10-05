"""Pytest plugin fixtures for jev-judge."""

import pytest
from jev_judge import Judge


@pytest.fixture
def jev_judge():
    """Pytest fixture providing a preconfigured Judge instance."""
    return Judge()
