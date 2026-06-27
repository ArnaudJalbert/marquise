"""Read-only public REST API for Marquise.

A thin FastAPI layer over the application read use cases. Handlers perform no
data access of their own — they delegate to use cases resolved from the DI
container. All endpoints are public (no authentication); admin mutations
remain CLI-only.
"""

from marquise.infrastructure.api.app import create_app

__all__ = ["create_app"]
