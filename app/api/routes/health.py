"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="API health check")
async def health():
    return {"status": "ok", "service": "indus11"}
