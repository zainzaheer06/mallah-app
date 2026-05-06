"""cart router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("/health")
async def cart_health() -> dict[str, str]:
    return {"module": "cart", "status": "scaffolded"}
