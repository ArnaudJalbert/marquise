"""Gateway protocols for data access.

Protocols (typing.Protocol) that define the interface between
interface_adapters and infrastructure.  Implementations reside in
``infrastructure/<tech>/gateways/`` and return plain dicts.
"""

from marquise.interface_adapters.repositories.protocols.auth import (
    AuthService,
    AuthSession,
)
from marquise.interface_adapters.repositories.protocols.cinema import (
    CinemaGateway,
    GatewayError,
)

__all__ = [
    "AuthService",
    "AuthSession",
    "CinemaGateway",
    "GatewayError",
]
