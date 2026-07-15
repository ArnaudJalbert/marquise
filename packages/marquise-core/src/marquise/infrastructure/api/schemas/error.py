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
                    "request_id": "1c1b0b4e-8f1b-4b8e-9b1e-1e1b0b4e8f1b",
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
    request_id: str | None = Field(
        default=None,
        description=(
            "The ID of the request that produced this error, also returned "
            "in the `X-Request-ID` response header. Include it when "
            "reporting an issue so the corresponding server log line can be "
            "found."
        ),
    )
