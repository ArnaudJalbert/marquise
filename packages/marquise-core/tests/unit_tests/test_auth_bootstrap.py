"""Tests for authentication composition in MarquiseFactory."""

from __future__ import annotations

from unittest.mock import create_autospec, patch

import pytest

from marquise.application.queries import VerifyAccessTokenQuery
from marquise.application.use_cases import (
    AuthenticateAdministratorUseCase,
    CreateBotUseCase,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
)
from marquise.bootstrap import MarquiseFactory
from marquise.infrastructure.di.container import Container


def test_factory_exposes_container_token_query() -> None:
    """Delivery consumes token verification through the shared container."""
    container = create_autospec(Container, instance=True)
    query = create_autospec(VerifyAccessTokenQuery, instance=True)
    container.verify_access_token_query = query

    with patch("marquise.bootstrap.Container", return_value=container):
        factory = MarquiseFactory()

    assert factory.verify_access_token_query is query


def test_factory_exposes_container_account_administration() -> None:
    """Every auth workflow is exposed through the shared factory."""
    container = create_autospec(Container, instance=True)
    authentication = create_autospec(
        AuthenticateAdministratorUseCase,
        instance=True,
    )
    invitation = create_autospec(InviteAccountUseCase, instance=True)
    bot_creation = create_autospec(CreateBotUseCase, instance=True)
    container.create_bot_use_case = bot_creation
    role_change = create_autospec(SetAccountRoleUseCase, instance=True)
    container.authenticate_administrator_use_case = authentication
    container.invite_account_use_case = invitation
    container.set_account_role_use_case = role_change

    with patch("marquise.bootstrap.Container", return_value=container):
        factory = MarquiseFactory()

    assert factory.authenticate_administrator_use_case is authentication
    assert factory.invite_account_use_case is invitation
    assert factory.set_account_role_use_case is role_change
    assert factory.create_bot_use_case is bot_creation


def test_factory_reports_unconfigured_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing Supabase configuration is explicit at capability access."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        _ = factory.verify_access_token_query


def test_factory_auth_does_not_require_database_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Token verification composition does not initialize or require a database."""
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    factory = MarquiseFactory()

    assert isinstance(factory.verify_access_token_query, VerifyAccessTokenQuery)
