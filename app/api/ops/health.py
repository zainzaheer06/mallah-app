"""Health and readiness probes — /health, /health/ready

No authentication. Used by load balancers and monitoring.
"""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.core import cache
from app.core.db import engine
from app.core.exceptions import ServiceUnavailable

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe (checks DB + Redis)")
async def readiness() -> dict[str, Any]:
    checks: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"failed: {e}"

    checks["redis"] = "ok" if await cache.ping() else "failed"

    if not all(v == "ok" for v in checks.values()):
        raise ServiceUnavailable(
            "One or more dependencies are unavailable", details=checks
        )

    return {"status": "ready", **checks}
