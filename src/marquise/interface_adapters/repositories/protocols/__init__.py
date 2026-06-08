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
from marquise.interface_adapters.repositories.protocols.cinema_source_assignment import (  # noqa: E501
    CinemaSourceAssignmentGateway as CinemaSourceAssignmentGateway,
)
from marquise.interface_adapters.repositories.protocols.movie import MovieGateway
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningGateway,
)
from marquise.interface_adapters.repositories.protocols.showtime_source import (
    ShowtimeSource,
)
from marquise.interface_adapters.repositories.protocols.source_definition import (
    SourceDefinitionGateway,
)

__all__ = [
    "AuthService",
    "AuthSession",
    "CinemaGateway",
    "CinemaSourceAssignmentGateway",
    "GatewayError",
    "MovieGateway",
    "ScreeningGateway",
    "ShowtimeSource",
    "SourceDefinitionGateway",
]
