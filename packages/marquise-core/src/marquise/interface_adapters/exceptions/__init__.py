"""Interface-adapter exceptions."""

from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayError,
    AuthGatewayUnavailableError,
)

__all__ = ["AuthGatewayError", "AuthGatewayUnavailableError"]
