import random
import time

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api", tags=["system-test"])


@router.get("/error-test")
def error_test() -> dict:
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "synthetic error for testing")


@router.get("/slow-test")
def slow_test() -> dict:
    delay_ms = random.randint(2000, 4000)
    time.sleep(delay_ms / 1000)
    return {"delayed_ms": delay_ms}
