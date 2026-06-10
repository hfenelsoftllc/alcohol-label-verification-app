# syntax=docker/dockerfile:1
#
# Frontend image — multi-stage: Node 20 build → nginx static serve.
# Build context is the repository root (see docker-compose.yml / CI).
# Base images are digest-pinned for a reproducible baseline (FedRAMP CM-2).

# ---- build stage --------------------------------------------------------
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS build

WORKDIR /app

# Install dependencies first (better caching). No lockfile is committed for the
# Phase 1 placeholder; ISSUE 1.5 introduces the React shell with a pinned lock.
COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./

# Base URL the SPA calls; nginx reverse-proxies /api to the backend by default.
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---- serve stage --------------------------------------------------------
FROM nginx:stable-alpine@sha256:5f979dcfed4ce6461873f087e8c980d6e29b084b9e8776d9704a7e989b5f4898

# Server config: SPA fallback + /api reverse proxy to the backend service.
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# nginx:alpine ships its own CMD; keep it.
