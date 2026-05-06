"""admin router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def admin_health() -> dict[str, str]:
    return {"module": "admin", "status": "scaffolded"}
