"""Authentication gateway failures translated by interface adapters."""


class AuthGatewayError(RuntimeError):
    """External authentication provider request failed."""


class AuthGatewayUnavailableError(AuthGatewayError):
    """External authentication provider is temporarily unavailable."""
