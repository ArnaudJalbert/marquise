"""The public facade offers catalog reads and imports, not Auth or manual edits."""

from __future__ import annotations

import pytest

import marquise

REMOVED_EXPORTS = {
    "AccountAlreadyExistsError",
    "AccountNotFoundError",
    "AuthAdministrationError",
    "AuthenticateAdministratorUseCase",
    "AuthenticationError",
    "AuthenticationServiceUnavailableError",
    "AuthorizationError",
    "CreateScreeningUseCase",
    "DeleteScreeningUseCase",
    "InviteAccountUseCase",
    "ScreeningIdempotencyConflictError",
    "ScreeningWriteBusyError",
    "SelfDemotionError",
    "SetAccountRoleUseCase",
    "VerifyAccessTokenQuery",
    "WriteScreeningUseCase",
}

REMOVED_FACTORY_MEMBERS = (
    "authenticate_administrator_use_case",
    "create_screening_use_case",
    "delete_screening_use_case",
    "invite_account_use_case",
    "set_account_role_use_case",
    "update_screening_use_case",
    "verify_access_token_query",
    "write_screening_use_case",
)


def test_facade_exports_no_auth_or_manual_screening_editing() -> None:
    """None of the removed Auth or screening-editing names is importable."""
    exported = set(marquise.__all__) | set(vars(marquise))

    assert REMOVED_EXPORTS.isdisjoint(exported)


def test_facade_keeps_import_and_query_entry_points() -> None:
    """Import commands and screening queries stay in the public surface."""
    assert {
        "ImportScreeningsCommand",
        "CreateScreeningsCommand",
        "SearchScreeningsQuery",
        "GetScreeningQuery",
    } <= set(marquise.__all__)


@pytest.mark.parametrize("member", REMOVED_FACTORY_MEMBERS)
def test_factory_offers_no_auth_or_manual_screening_editing(member: str) -> None:
    """The configured factory exposes no removed use case or query."""
    assert not hasattr(marquise.MarquiseFactory, member)
