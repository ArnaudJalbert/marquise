"""Error envelope response model for the read-only API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """The standard error envelope returned by all API error responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "detail": "Cinema 'cinema-does-not-exist' was not found.",
                    "error_code": "not_found",
                }
            ]
        }
    )

    detail: str = Field(description="A human-readable explanation of the error.")
    error_code: str = Field(
        description=(
            "A stable, machine-readable error identifier (e.g. `not_found`, "
            "`invalid_input`, `conflict`, `internal_server_error`). Prefer "
            "matching on this field over parsing `detail`, whose wording may "
            "change."
        )
    )
