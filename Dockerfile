# ==============================================================================
# SICRA Backend Multi-Stage Production Dockerfile
# Optimized for Render Free Tier (< 512 MB RAM Footprint & < 600 MB Image Size)
# ==============================================================================

# Stage 1: Build & Dependency Wheel Cache
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Lean Production Runtime (< 512 MB RAM Footprint)
FROM python:3.12-slim AS runner

WORKDIR /app

# Install wheels directly from builder without persisting redundant wheel archives
RUN --mount=type=bind,from=builder,source=/app/wheels,target=/wheels \
    pip install --no-cache-dir /wheels/* \
    && find /usr/local -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local -type d -name "test" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local -name "*.pyc" -delete \
    && find /usr/local -name "*.pyo" -delete

# Create non-privileged user for security
RUN addgroup --system sicragroup && adduser --system --group sicrauser

# Copy application source, migrations, configuration, and trained models
COPY src/ /app/src/
COPY data/ /app/data/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY models/ /app/models/

# Grant execution permissions
RUN chown -R sicrauser:sicragroup /app

USER sicrauser

# Render dynamically injects $PORT (default 10000)
ENV PORT=10000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE ${PORT}

# Startup command: Run lightweight single-worker uvicorn
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1
