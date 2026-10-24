FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install .

RUN useradd --create-home --uid 10001 musicat \
    && mkdir -p /data \
    && chown -R musicat:musicat /data /app

USER musicat

ENV MUSICAT_DATA_DIR=/data \
    MUSICAT_HOST=0.0.0.0 \
    MUSICAT_PORT=8000 \
    MUSICAT_OPEN_BROWSER=0 \
    MUSICAT_STRICT_PORT=1 \
    MUSICAT_CLAIM_LEGACY=0

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)" || exit 1

CMD ["python", "-m", "musicat"]
