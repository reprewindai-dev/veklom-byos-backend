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
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --wheel-dir /wheels -r requirements.txt


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 veklom && \
    useradd --system --uid 10001 --gid 10001 --create-home veklom

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels /root/.cache

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY irongrid/dist/ ./irongrid/dist/
COPY uacp-quantum-terminal.html .
COPY agents/ ./agents/

RUN mkdir -p /app/logs && chown -R veklom:veklom /app
USER veklom

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import os,sys,urllib.request; p=os.getenv('PORT','8088'); u=f'http://127.0.0.1:{p}/health'; sys.exit(0 if urllib.request.urlopen(u, timeout=5).status==200 else 1)"

CMD ["python", "-m", "backend.apps.api.dualstack_server"]
