"""Public bootstrap API for configured Marquise use cases."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from marquise.infrastructure.di.factory import MarquiseFactory


async def create_factory() -> MarquiseFactory:
    """Create and initialize a :class:`MarquiseFactory`.

    Returns:
        A fully initialized factory ready to execute configured use cases.
    """
    factory = MarquiseFactory()
    await factory.initialize()
    return factory


@asynccontextmanager
async def create_factory_session() -> AsyncGenerator[MarquiseFactory]:
    """Context-manager variant of :func:`create_factory`.

    Automatically shuts down factory when ``async with`` block exits::

        async with create_factory_session() as factory:
            use_case = factory.list_cinemas_use_case
            result = await use_case.execute(use_case.InputData())
    """
    factory = MarquiseFactory()
    await factory.initialize()
    try:
        yield factory
    finally:
        await factory.shutdown()
