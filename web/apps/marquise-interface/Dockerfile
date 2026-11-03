FROM node:22-alpine AS builder

RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/marquise-interface/package.json ./apps/marquise-interface/
COPY packages/components/package.json ./packages/components/
COPY packages/marquise-client/package.json ./packages/marquise-client/

RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_MARQUISE_API_BASE_URL=https://api.marquise.mov
ENV VITE_MARQUISE_API_BASE_URL=$VITE_MARQUISE_API_BASE_URL

RUN pnpm --filter marquise-client build \
    && pnpm --filter marquise-components build \
    && pnpm --filter marquise-interface build

FROM nginx:1.27-alpine

COPY apps/marquise-interface/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/marquise-interface/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
