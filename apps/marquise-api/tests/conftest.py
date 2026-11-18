"""Shared fixtures for the API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import ExitStack, asynccontextmanager
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from marquise_api.app import create_app


@pytest.fixture
def open_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Callable[..., TestClient]]:
    """Provide a function that serves the app over a fake factory.

    The function patches create_factory_session to yield the given fake, then
    enters a TestClient so the real lifespan runs, as it does in production.
    Every client it opens closes when the test ends.
    """
    with ExitStack() as stack:

        def open_client(factory: MagicMock, **client_options: bool) -> TestClient:
            @asynccontextmanager
            async def fake_factory_session() -> AsyncIterator[MagicMock]:
                yield factory

            monkeypatch.setattr(
                "marquise_api.app.create_factory_session", fake_factory_session
            )
            return stack.enter_context(TestClient(create_app(), **client_options))

        yield open_client
