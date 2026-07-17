# Multi-stage Dockerfile for the marquise-interface poster-wall SPA.
#
# Build stage installs the pnpm workspace and produces a static production
# build (pointed at the live production API). Final stage serves it via nginx.
#
# Usage
# -----
#     docker build -t marquise-interface -f apps/marquise-interface/Dockerfile .
#     docker run --rm -p 8080:80 marquise-interface
#
# Must be built with `web/` as the build context (this app depends on
# workspace-local packages via `workspace:*`, e.g. @marquise/components).

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM node:22-alpine AS builder

RUN corepack enable

WORKDIR /app

# Copy workspace manifests first to maximise Docker layer caching.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/marquise-interface/package.json ./apps/marquise-interface/
COPY apps/marquise-admin/package.json ./apps/marquise-admin/
COPY packages/api-client/package.json ./packages/api-client/
COPY packages/components/package.json ./packages/components/

RUN pnpm install --frozen-lockfile

# Copy the source tree and build the interface app against the live API.
COPY . .
RUN pnpm --filter marquise-interface build:live-remote

# ---------------------------------------------------------------------------
# Stage 2 — final
# ---------------------------------------------------------------------------
FROM nginx:alpine

COPY apps/marquise-interface/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/marquise-interface/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
