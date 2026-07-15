# Multi-stage Dockerfile for the Marquise read-only API.
#
# Build stage installs production dependencies via uv and copies the source.
# Final stage runs uvicorn as a non-root user.
#
# Usage
# -----
#     docker build -t marquise-api -f apps/marquise-api/Dockerfile .
#     docker run --rm -p 8000:8000 \
#         -e DATABASE_URL=... \
#         -e SUPABASE_URL=... \
#         -e SUPABASE_PUBLISHABLE_KEY=... \
#         marquise-api

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

# Install uv via the official static binary (no curl/pip needed in the image).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Optimisation flags for Docker layer caching.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency manifests first to maximise Docker layer caching.
# README.md is required by hatchling's metadata validation at build time.
COPY pyproject.toml uv.lock ./
COPY packages/marquise-core/pyproject.toml packages/marquise-core/README.md ./packages/marquise-core/
COPY apps/marquise-api/pyproject.toml ./apps/marquise-api/

# Install all production dependencies (no dev group) without the project itself.
RUN uv sync --frozen --no-dev --no-install-project --package marquise-api

# Copy the source tree and install the project into the same venv.
COPY packages/marquise-core/src/ ./packages/marquise-core/src/
COPY apps/marquise-api/src/ ./apps/marquise-api/src/
RUN uv sync --frozen --no-dev --package marquise-api

# ---------------------------------------------------------------------------
# Stage 2 — final
# ---------------------------------------------------------------------------
FROM python:3.13-slim

# Create a non-root user.
RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copy the virtual environment and source from the builder stage.
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/packages/marquise-core/src /app/packages/marquise-core/src
COPY --from=builder --chown=appuser:appuser /app/apps/marquise-api/src /app/apps/marquise-api/src

# Make the venv's bin directory available in PATH.
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

CMD ["uvicorn", "marquise_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
