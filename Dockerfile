# Veklom BYOS Backend — Dockerfile for Coolify Deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY uacp-quantum-terminal.html .

# Create log directory
RUN mkdir -p /app/logs && \
    useradd -m -u 1000 veklom && \
    chown -R veklom:veklom /app
USER veklom

# Expose port
EXPOSE 8088

# Health check (Coolify compatible). Follow the runtime PORT so a Coolify
# port override does not make the new container fail health checks.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c 'curl -f "http://localhost:${PORT:-8088}/health" || exit 1'

# Run with uvicorn (PORT can be overridden by Coolify)
CMD ["sh", "-c", "uvicorn backend.apps.api.main:app --host 0.0.0.0 --port ${PORT:-8088}"]
