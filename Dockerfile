# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system deps (curl for healthchecks/logs if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    bash \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY main.py ./
COPY src ./src
COPY entrypoint.sh /entrypoint.sh

# Ensure entrypoint is executable
RUN chmod +x /entrypoint.sh

# Default environment (override in compose or docker run)
ENV SYNC_INTERVAL_MINUTES=5 \
    DEBUG=false

# Healthcheck: process should be running and produce logs
HEALTHCHECK --interval=1m --timeout=10s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "python -u /app/main.py" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
