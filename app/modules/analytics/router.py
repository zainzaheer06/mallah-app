"""analytics router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/health")
async def analytics_health() -> dict[str, str]:
    return {"module": "analytics", "status": "scaffolded"}
