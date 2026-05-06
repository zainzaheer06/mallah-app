"""ingest router — placeholder.

Endpoints will be added in the appropriate deliverable (D2-D6).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/health")
async def ingest_health() -> dict[str, str]:
    return {"module": "ingest", "status": "scaffolded"}
