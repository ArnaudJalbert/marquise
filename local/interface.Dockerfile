# Local built React app. Copy source/config explicitly, never any .env files.
FROM node:24-alpine AS builder
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json tsconfig.base.json ./
COPY apps/marquise-interface/package.json ./apps/marquise-interface/
COPY packages/components/package.json ./packages/components/
COPY packages/marquise-client/package.json ./packages/marquise-client/
RUN pnpm install --frozen-lockfile
COPY packages/marquise-client/src ./packages/marquise-client/src
COPY packages/marquise-client/tsconfig*.json packages/marquise-client/vite.config.ts ./packages/marquise-client/
COPY packages/components/src ./packages/components/src
COPY packages/components/tsconfig*.json packages/components/vite.config.ts ./packages/components/
COPY packages/components/demo/check-isolation.mjs ./packages/components/demo/
COPY apps/marquise-interface/src ./apps/marquise-interface/src
COPY apps/marquise-interface/tsconfig*.json apps/marquise-interface/vite.config.ts apps/marquise-interface/index.html ./apps/marquise-interface/
COPY apps/marquise-interface/scripts ./apps/marquise-interface/scripts
COPY apps/marquise-interface/public ./apps/marquise-interface/public
ENV VITE_MARQUISE_API_BASE_URL=""
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=builder /app/apps/marquise-interface/dist /usr/share/nginx/html
EXPOSE 80
