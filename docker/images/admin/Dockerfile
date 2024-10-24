FROM node:18.20-slim as builder

WORKDIR /app

COPY src/frontend/admin .
ARG NEXT_PUBLIC_API_SOURCE=backend
ARG NEXT_PUBLIC_API_ENDPOINT
ARG NEXT_PUBLIC_DJANGO_ADMIN_BASE_URL

RUN yarn install --frozen-lockfile && \
    yarn build

FROM nginxinc/nginx-unprivileged:1.25 as production

COPY docker/files/admin/etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/out /app/admin
