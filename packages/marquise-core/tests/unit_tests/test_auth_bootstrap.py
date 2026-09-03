"""Tests for authentication composition in MarquiseFactory."""

from __future__ import annotations

from unittest.mock import create_autospec, patch

import pytest

from marquise.application.queries import VerifyAccessTokenQuery
from marquise.auth_factory import AuthFactory
from marquise.bootstrap import MarquiseFactory


def test_factory_exposes_injected_token_query() -> None:
    """Delivery can consume auth through the shared configured factory."""
    auth_factory = create_autospec(AuthFactory, instance=True)
    query = create_autospec(VerifyAccessTokenQuery, instance=True)
    auth_factory.verify_access_token_query = query

    with patch("marquise.bootstrap.Container"):
        factory = MarquiseFactory(auth_factory=auth_factory)

    assert factory.verify_access_token_query is query


def test_factory_reports_unconfigured_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing Supabase configuration is explicit at capability access."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)

    with patch("marquise.bootstrap.Container"):
        factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        _ = factory.verify_access_token_query
