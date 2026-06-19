import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.routes import auth, dashboard, health, aiops, cicd

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
app.include_router(aiops.router)
app.include_router(cicd.router)


@app.get("/sonar-api/{path:path}")
async def sonar_proxy(path: str, request: Request):
    params = dict(request.query_params)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://sonarcloud.io/api/{path}",
            params=params,
            headers={"Authorization": request.headers.get("Authorization", "")},
        )
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type=resp.headers.get("content-type"))


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def root():
        return {"service": "admin-service", "docs": "/docs"}
