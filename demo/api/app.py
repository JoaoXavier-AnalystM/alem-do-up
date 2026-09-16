import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:  # pragma: no cover - allows lightweight static inspection
    trace = None
    AsyncPGInstrumentor = None
    FastAPIInstrumentor = None


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
logger = logging.getLogger("checkout-api")

REQUESTS = Counter("checkout_http_requests_total", "HTTP requests", ["path", "method", "status"])
ERRORS = Counter("checkout_errors_total", "Checkout errors", ["reason"])
LATENCY = Histogram("checkout_http_request_duration_seconds", "Request duration", ["path"], buckets=(.05, .1, .25, .5, 1, 2, 5, 10, 20))
POOL_IN_USE = Gauge("checkout_db_pool_in_use", "Connections currently held by demo work")
POOL_WAITING = Gauge("checkout_db_pool_waiting", "Requests waiting for a pool connection")
POOL_SIZE = Gauge("checkout_db_pool_size", "Configured pool size")
INCIDENT = Gauge("checkout_demo_incident", "1 while incident mode is enabled")


@dataclass
class DemoState:
    mode: str = "normal"
    pool_in_use: int = 0
    pool_size: int = int(os.getenv("DB_POOL_MAX", "5"))
    hold_seconds: float = float(os.getenv("INCIDENT_HOLD_SECONDS", "8"))
    waiting: int = 0


demo_state = DemoState()
app = FastAPI(title="Checkout API — UP but not healthy")
db_pool: asyncpg.Pool | None = None


class DemoStateRequest(BaseModel):
    mode: str


if trace and os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "checkout-api")}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    if FastAPIInstrumentor:
        FastAPIInstrumentor.instrument_app(app)


def emit(event: str, **fields):
    logger.info(json.dumps({"event": event, "service": "checkout-api", **fields}))


def health_payload():
    pool_exhausted = demo_state.pool_in_use >= demo_state.pool_size
    degraded = demo_state.mode == "incident" and pool_exhausted
    return {
        "status": "degraded" if degraded else "ok",
        "http_status": 503 if degraded else 200,
        "mode": demo_state.mode,
        "pool_in_use": demo_state.pool_in_use,
        "pool_size": demo_state.pool_size,
        "message": "basic process health; business latency may still be degraded" if not degraded else "pool capacity exhausted",
    }


@app.on_event("startup")
async def startup():
    global db_pool
    if AsyncPGInstrumentor:
        AsyncPGInstrumentor().instrument()
    for attempt in range(30):
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                database_url = "postgresql://{user}:{password}@{host}:{port}/{name}".format(
                    user=os.environ["APP_DB_USER"],
                    password=os.environ["APP_DB_PASSWORD"],
                    host=os.getenv("APP_DB_HOST", "db"),
                    port=os.getenv("APP_DB_PORT", "5432"),
                    name=os.environ["APP_DB_NAME"],
                )
            db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=demo_state.pool_size)
            POOL_SIZE.set(demo_state.pool_size)
            emit("database_pool_ready", pool_size=demo_state.pool_size)
            return
        except Exception as exc:
            emit("database_waiting", attempt=attempt + 1, error=str(exc))
            await asyncio.sleep(1)
    raise RuntimeError("database did not become ready")


@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()


@app.get("/health")
async def health():
    payload = health_payload()
    return JSONResponse(payload, status_code=payload["http_status"])


@app.get("/metrics")
async def metrics():
    POOL_IN_USE.set(demo_state.pool_in_use)
    POOL_WAITING.set(demo_state.waiting)
    INCIDENT.set(1 if demo_state.mode == "incident" else 0)
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/demo/state")
async def set_state(request: DemoStateRequest):
    if request.mode not in {"normal", "incident"}:
        raise HTTPException(400, "mode must be normal or incident")
    demo_state.mode = request.mode
    emit("demo_state_changed", mode=request.mode)
    return {"mode": request.mode, "health": health_payload()}


async def hold_connection(seconds: float):
    if not db_pool:
        raise RuntimeError("database pool not ready")
    demo_state.waiting += 1
    try:
        async with db_pool.acquire(timeout=2) as conn:
            demo_state.waiting -= 1
            demo_state.pool_in_use += 1
            POOL_IN_USE.set(demo_state.pool_in_use)
            await conn.execute("SELECT pg_sleep($1)", seconds)
            demo_state.pool_in_use -= 1
            return True
    except (asyncio.TimeoutError, asyncpg.exceptions.TooManyConnectionsError):
        demo_state.waiting = max(0, demo_state.waiting - 1)
        ERRORS.labels("pool_exhausted").inc()
        emit("db_pool_exhausted", pool_in_use=demo_state.pool_in_use, pool_size=demo_state.pool_size, waiting=demo_state.waiting)
        return False


@app.post("/demo/hold")
async def demo_hold(seconds: float | None = None):
    seconds = seconds or demo_state.hold_seconds
    if demo_state.mode != "incident":
        return {"accepted": False, "message": "set incident mode first"}
    accepted = await hold_connection(seconds)
    return JSONResponse({"accepted": accepted, "pool_in_use": demo_state.pool_in_use}, status_code=200 if accepted else 503)


@app.get("/checkout")
async def checkout():
    started = time.perf_counter()
    status = "200"
    try:
        seconds = 0.08 if demo_state.mode == "normal" else 0.35
        if demo_state.mode == "incident":
            ok = await hold_connection(seconds)
            if not ok:
                status = "503"
                raise HTTPException(503, "checkout database pool exhausted")
        elif db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
        return {"status": "confirmed", "mode": demo_state.mode}
    except HTTPException:
        ERRORS.labels("checkout_failed").inc()
        emit("checkout_failed", reason="pool_exhausted")
        raise
    finally:
        duration = time.perf_counter() - started
        LATENCY.labels("/checkout").observe(duration)
        REQUESTS.labels("/checkout", "GET", status).inc()


@app.get("/")
async def root():
    return {"service": "checkout-api", "links": ["/health", "/metrics", "/checkout"]}
