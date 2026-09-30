# Build Render (contexte = racine du depot). Meme image que backend/Dockerfile.
# Alternative dashboard : Root Directory = backend, Dockerfile = Dockerfile (sans ce fichier).

FROM python:3.12-slim-bookworm AS runtime
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/auth ./auth/
COPY backend/events ./events/
COPY backend/http_layer ./http_layer/
COPY backend/money ./money/
COPY backend/notify ./notify/
COPY backend/orders ./orders/
COPY backend/payments ./payments/
COPY backend/scan ./scan/
COPY backend/store ./store/
COPY backend/tickets ./tickets/
COPY backend/cli.py backend/config.py backend/bootstrap.py backend/spa.py backend/__init__.py backend/__main__.py ./
COPY backend/migrations ./migrations
COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN pip install --no-cache-dir .

RUN mkdir -p /srv/data/media && chown -R app:app /srv/data /app

USER app
WORKDIR /srv/data

ENV CHANTIER3A_ADDR=":8080" \
    CHANTIER3A_DATA_DIR="/srv/data" \
    CHANTIER3A_MEDIA_DIR="/srv/data/media"

VOLUME ["/srv/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; p=os.environ.get('PORT','8080'); urllib.request.urlopen(f'http://127.0.0.1:{p}/healthz', timeout=2)"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["serve"]
