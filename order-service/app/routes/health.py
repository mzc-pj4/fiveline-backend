from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name, "env": settings.environment, "version": "1.0.1"}
