"""compare router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/health")
async def compare_health() -> dict[str, str]:
    return {"module": "compare", "status": "scaffolded"}
