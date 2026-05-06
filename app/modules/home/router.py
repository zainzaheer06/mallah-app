"""home router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/health")
async def home_health() -> dict[str, str]:
    return {"module": "home", "status": "scaffolded"}
