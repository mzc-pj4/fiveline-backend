from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware import AccessLogMiddleware
from app.routes import cart, health, orders, system

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "status_code", "handler"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="order-service",
    version="0.1.0",
    description="mzc-pj4 cart + orders + failure simulation",
    lifespan=lifespan,
)

app.add_middleware(AccessLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "https://d330d0cjfkz4e7.cloudfront.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(system.router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(
        method=request.method,
        status_code=str(response.status_code),
        handler=request.url.path,
    ).inc()
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.service_name, "version": "1.0.4", "docs": "/docs"}
