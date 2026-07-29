# Multi-stage Dockerfile for the Marquise CLI.
#
# Build stage installs production dependencies via uv and copies the source.
# Final stage runs the CLI (default: --help).
#
# Usage
# -----
#     docker build -t marquise-cli -f apps/marquise-cli/Dockerfile .
#     docker run --rm marquise-cli --help
#     docker run --rm marquise-cli cinema list

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/marquise-core/pyproject.toml packages/marquise-core/README.md ./packages/marquise-core/
COPY apps/marquise-cli/pyproject.toml ./apps/marquise-cli/

RUN uv sync --frozen --no-dev --no-install-project --package marquise-cli

COPY packages/marquise-core/src/ ./packages/marquise-core/src/
COPY apps/marquise-cli/src/ ./apps/marquise-cli/src/
RUN uv sync --frozen --no-dev --package marquise-cli

# ---------------------------------------------------------------------------
# Stage 2 — final
# ---------------------------------------------------------------------------
FROM python:3.13-slim

RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/packages/marquise-core/src /app/packages/marquise-core/src
COPY --from=builder --chown=appuser:appuser /app/apps/marquise-cli/src /app/apps/marquise-cli/src

ENV PATH="/app/.venv/bin:$PATH"

USER appuser

ENTRYPOINT ["marquise"]
CMD ["--help"]
