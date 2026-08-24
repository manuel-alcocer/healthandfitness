# Frontend image: Vite build served by nginx, which also fronts the API so the
# browser only ever talks to one origin.
FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# The unprivileged variant runs as uid 101 and listens on 8080, so the
# container needs no capabilities at all.
FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime

# BACKEND_URL is substituted into the config at container start, so the same
# image works in compose and in the cluster.
ENV BACKEND_URL=http://backend:8000

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
