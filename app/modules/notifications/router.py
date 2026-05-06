"""notifications router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/health")
async def notifications_health() -> dict[str, str]:
    return {"module": "notifications", "status": "scaffolded"}
