"""W2 dev-only failure/latency simulation.

Used to populate realistic ORDER_FAILED / SLOW_RESPONSE events so the
downstream observability (CW Metrics, Athena, Bedrock Agent) has
something to analyze. Tunable via FAILURE_RATE / SLOW_RATE env vars.
"""

import random
import time

from app.core.config import settings

FAILURE_CODES = (
    "OUT_OF_STOCK",
    "PAYMENT_FAILED_SIMULATED",
    "DB_TIMEOUT",
    "INTERNAL_SERVER_ERROR",
)


def maybe_fail() -> str | None:
    if random.random() < settings.failure_rate:
        return random.choice(FAILURE_CODES)
    return None


def maybe_delay() -> int:
    """Sleep a random amount when SLOW_RATE triggers, return slept ms (0 if not slow)."""
    if random.random() < settings.slow_rate:
        ms = random.randint(settings.slow_response_ms_min, settings.slow_response_ms_max)
        time.sleep(ms / 1000)
        return ms
    return 0
