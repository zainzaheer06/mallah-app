"""
FastAPI application entrypoint.

Composition order matters:
  1. Initialize logging + Sentry (so startup errors are captured)
  2. Build the FastAPI app
  3. Register middleware (CORS, request_id, rate limit)
  4. Register exception handlers
  5. Mount module routers under /api/v1
  6. Healthchecks at root level
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: F401

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.modules.admin.router import router as admin_router
from app.modules.analytics.router import router as analytics_router
from app.api.consumer.auth import router as auth_router
from app.api.consumer.me import router as me_router
from app.api.ops.health import router as health_router
from app.modules.cart.router import router as cart_router
from app.modules.catalog.router import router as catalog_router
from app.modules.compare.router import router as compare_router
from app.modules.favorites.router import router as favorites_router
from app.modules.home.router import router as home_router
from app.modules.ingest.router import router as ingest_router
from app.modules.notifications.router import router as notifications_router
from app.modules.search.router import router as search_router

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
configure_logging()
logger = structlog.get_logger()

# Sentry is optional — only initialize if DSN is set AND sentry_sdk is installed
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            release=settings.APP_VERSION,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        logger.info("sentry_initialized")
    except ImportError:
        logger.warning("sentry_dsn_set_but_sdk_missing")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app_starting",
        env=settings.APP_ENV,
        version=settings.APP_VERSION,
        firebase=settings.firebase_enabled,
        email=settings.email_enabled,
    )
    yield
    from app.core import cache as _cache
    await _cache.close()
    logger.info("app_stopping")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_IP_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL,
    storage_options={"socket_connect_timeout": 2},
    strategy="fixed-window",
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.APP_DEBUG,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.state.limiter = limiter


# ---------------------------------------------------------------------------
# Middleware (registration order matters: outermost first)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SlowAPIMiddleware)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    """Map domain exceptions -> standardized JSON error payload."""
    body: dict[str, Any] = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
        }
    }
    if exc.details:
        body["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=body)


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/", tags=["health"], summary="Root")
async def root() -> dict[str, str]:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"], summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"], summary="Readiness probe (checks DB + Redis)")
async def readiness() -> dict[str, Any]:
    from sqlalchemy import text
    from app.core import cache
    from app.core.db import engine
    from app.core.exceptions import ServiceUnavailable

    checks: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"failed: {e}"

    checks["redis"] = "ok" if await cache.ping() else "failed"

    all_ok = all(v == "ok" for v in checks.values())
    if not all_ok:
        raise ServiceUnavailable("One or more dependencies are unavailable", details=checks)

    return {"status": "ready", **checks}
# ---------------------------------------------------------------------------
# Router composition
# ---------------------------------------------------------------------------
api = settings.API_V1_PREFIX

# D1 — auth + me (production-grade)
app.include_router(auth_router, prefix=api)
app.include_router(me_router, prefix=api)

# D2-D6 — scaffolded, ready to fill in
app.include_router(catalog_router, prefix=api)
app.include_router(ingest_router, prefix=api)
app.include_router(home_router, prefix=api)
app.include_router(search_router, prefix=api)
app.include_router(compare_router, prefix=api)
app.include_router(cart_router, prefix=api)
app.include_router(favorites_router, prefix=api)
app.include_router(notifications_router, prefix=api)
app.include_router(admin_router, prefix=api)
app.include_router(analytics_router, prefix=api)
