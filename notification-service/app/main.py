from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, notifications
from app.sqs_consumer import start_sqs_consumer


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_sqs_consumer()
    yield


app = FastAPI(title="notification-service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "https://d330d0cjfkz4e7.cloudfront.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(notifications.router)


@app.get("/")
def root():
    return {"service": "notification-service", "docs": "/docs"}
