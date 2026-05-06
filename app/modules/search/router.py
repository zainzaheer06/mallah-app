"""search router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/health")
async def search_health() -> dict[str, str]:
    return {"module": "search", "status": "scaffolded"}
