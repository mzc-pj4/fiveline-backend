from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health():
    return {"status": "ok", "service": "admin-service", "version": "1.0.0"}
