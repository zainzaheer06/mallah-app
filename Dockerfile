# syntax=docker/dockerfile:1.6
# =============================================================================
# Mallah Backend — Multi-stage Dockerfile
# Stage 1: builder  -> compiles wheels
# Stage 2: runtime  -> slim image with only runtime deps
# =============================================================================

# --- Stage 1: builder --------------------------------------------------------
FROM python:3.14-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml ./

RUN pip install --upgrade pip && \
    pip wheel --wheel-dir=/wheels \
        "fastapi>=0.110.0" "uvicorn[standard]>=0.27.0" "gunicorn>=21.2.0" \
        "sqlalchemy>=2.0.25" "alembic>=1.13.0" "psycopg[binary]>=3.1.18" "asyncpg>=0.29.0" \
        "pydantic>=2.6.0" "pydantic-settings>=2.1.0" "email-validator>=2.1.0" \
        "python-jose[cryptography]>=3.3.0" "bcrypt>=4.1.0" "python-multipart>=0.0.9" \
        "firebase-admin>=6.4.0" "redis>=5.0.0" "slowapi>=0.1.9" \
        "sendgrid>=6.11.0" "sentry-sdk[fastapi]>=1.40.0" "structlog>=24.1.0" \
        "httpx>=0.26.0" "tenacity>=8.2.0" "python-dotenv>=1.0.0"

# --- Stage 2: runtime --------------------------------------------------------
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

# libpq5 for psycopg, dumb-init for proper signal forwarding under Docker
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    dumb-init \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 mallah
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY --chown=mallah:mallah . .

USER mallah

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/health || exit 1

ENTRYPOINT ["dumb-init", "--"]
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "60", \
     "--graceful-timeout", "30"]
