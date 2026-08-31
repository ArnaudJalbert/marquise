"""Shared fixtures for marquise-cli tests."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest

from cli_helpers import mock_use_case
from marquise import ListCinemasUseCase, MarquiseFactory


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.__aenter__.return_value = factory
    factory.__aexit__.return_value = False
    return factory


@pytest.fixture
def mock_list_cinemas_use_case() -> MagicMock:
    """Provide a mocked ListCinemasUseCase."""
    return mock_use_case(ListCinemasUseCase)
