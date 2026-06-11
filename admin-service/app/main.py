import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes import auth, dashboard, health

STATIC_DIR = Path(__file__).parent.parent / "static"

app = FastAPI(title="admin-service", version="1.0.0")

# 로컬 개발 기본값 + 환경변수로 CloudFront URL 주입 (ADMIN_CORS_ORIGINS=https://xxxx.cloudfront.net)
_extra_origins = [o for o in os.getenv("ADMIN_CORS_ORIGINS", "").split(",") if o]
ALLOWED_ORIGINS = [
    "http://localhost:8004",
    "http://127.0.0.1:8004",
    "http://localhost:5173",
] + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(dashboard.router)

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def root():
        return {"service": "admin-service", "docs": "/docs"}
