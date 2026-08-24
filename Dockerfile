# Veklom BYOS Backend - hardened multi-stage image for Coolify deployment
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --retries 10 --timeout 60 setuptools wheel && \
    python -m pip wheel --wheel-dir /wheels --no-cache-dir --retries 10 --timeout 60 -r requirements.txt


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
LABEL veklom.workload="backend-api"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 veklom && \
    useradd --system --uid 10001 --gid 10001 --create-home veklom

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels /root/.cache

COPY backend/ ./backend/
COPY pyproject.toml ./
COPY frontend/ ./frontend/
COPY agents/ ./agents/
COPY scripts/ ./scripts/
COPY backend/tests/ ./backend/tests/
COPY migrations/ ./migrations/

RUN mkdir -p /app/logs && chown -R veklom:veklom /app
USER veklom

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:8088/health/dependencies || exit 1

CMD ["uvicorn", "backend.apps.api.main:app", "--host", "0.0.0.0", "--port", "8088", "--workers", "3"]
