"""favorites router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/health")
async def favorites_health() -> dict[str, str]:
    return {"module": "favorites", "status": "scaffolded"}
