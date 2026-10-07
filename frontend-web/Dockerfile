# Image de production du front (vitrine + billetterie).
# Build Vite puis service statique par Caddy, avec repli SPA sur index.html.
# L'API est servie sur le meme domaine (/api, /media) par le proxy du serveur :
# VITE_API_URL reste vide, les variables publiques viennent de .env.production.

FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2.11-alpine
COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
