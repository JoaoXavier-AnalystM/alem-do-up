import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
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
VALID_MODES = {"normal", "degraded", "incident", "offline", "progressive"}
DEMO_STAGE_SECONDS = float(os.getenv("DEMO_STAGE_SECONDS", "30"))
DEGRADED_DELAY_SECONDS = float(os.getenv("DEGRADED_DELAY_SECONDS", "2"))
DEMO_DEGRADED_AFTER = int(os.getenv("DEMO_DEGRADED_AFTER", "10"))
DEMO_CRITICAL_AFTER = int(os.getenv("DEMO_CRITICAL_AFTER", "20"))
DEMO_OFFLINE_AFTER = int(os.getenv("DEMO_OFFLINE_AFTER", "25"))


@dataclass
class DemoState:
    mode: str = "normal"
    pool_in_use: int = 0
    pool_size: int = int(os.getenv("DB_POOL_MAX", "5"))
    hold_seconds: float = float(os.getenv("INCIDENT_HOLD_SECONDS", "8"))
    waiting: int = 0
    submissions: int = 0


demo_state = DemoState()
app = FastAPI(title="Checkout API — UP but not healthy")
db_pool: asyncpg.Pool | None = None
UI_PREFIX = os.getenv("APP_UI_PREFIX", "demo").strip("/") or "demo"
UI_FILE = Path(__file__).parent / "ui" / "index.html"
SHOP_FILE = Path(__file__).parent / "ui" / "shop.html"
progression_task: asyncio.Task | None = None


class DemoStateRequest(BaseModel):
    mode: str


class CheckoutSubmission(BaseModel):
    name: str
    age: int
    profession: str


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
    critical = demo_state.mode == "incident" and (pool_exhausted or demo_state.submissions >= DEMO_CRITICAL_AFTER)
    degraded = demo_state.mode == "incident" and critical
    if demo_state.mode == "offline":
        status = "offline"
        http_status = 503
        message = "checkout service unavailable"
    elif demo_state.mode == "degraded":
        status = "degraded"
        http_status = 200
        message = "business latency is degraded"
    else:
        status = "degraded" if degraded else "ok"
        http_status = 503 if degraded else 200
        message = "pool capacity exhausted" if degraded else "basic process health; business latency may still be degraded"
    return {
        "status": status,
        "http_status": http_status,
        "mode": demo_state.mode,
        "pool_in_use": demo_state.pool_in_use,
        "pool_size": demo_state.pool_size,
        "waiting": demo_state.waiting,
        "message": message,
        "submissions": demo_state.submissions,
        "thresholds": {"degraded": DEMO_DEGRADED_AFTER, "critical": DEMO_CRITICAL_AFTER, "offline": DEMO_OFFLINE_AFTER},
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
    await cancel_progression()
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


@app.get(f"/{UI_PREFIX}", include_in_schema=False)
async def presentation_ui():
    return FileResponse(UI_FILE)


@app.get("/comprar", include_in_schema=False)
async def shop_ui():
    return FileResponse(SHOP_FILE)


async def cancel_progression():
    global progression_task
    if progression_task and not progression_task.done():
        progression_task.cancel()
        try:
            await progression_task
        except asyncio.CancelledError:
            pass
    progression_task = None


async def run_progression():
    for mode in ("degraded", "incident", "offline"):
        await asyncio.sleep(DEMO_STAGE_SECONDS)
        demo_state.mode = mode
        emit("demo_progression_stage", mode=mode)
        if mode == "incident":
            holds = [
                hold_connection(max(DEMO_STAGE_SECONDS, demo_state.hold_seconds))
                for _ in range(demo_state.pool_size + 2)
            ]
            await asyncio.gather(*holds, return_exceptions=True)


@app.post("/demo/state")
async def set_state(request: DemoStateRequest):
    global progression_task
    if request.mode not in VALID_MODES:
        raise HTTPException(400, "mode must be normal, degraded, incident, offline, or progressive")
    await cancel_progression()
    if request.mode == "progressive":
        demo_state.mode = "normal"
        demo_state.submissions = 0
        progression_task = asyncio.create_task(run_progression())
        emit("demo_progression_started", stage_seconds=DEMO_STAGE_SECONDS)
        return {"mode": request.mode, "health": health_payload(), "progression": True}
    demo_state.mode = request.mode
    if request.mode == "normal":
        demo_state.submissions = 0
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


def register_submission():
    demo_state.submissions += 1
    if demo_state.submissions >= DEMO_OFFLINE_AFTER:
        demo_state.mode = "offline"
        threshold = "offline"
    elif demo_state.submissions >= DEMO_CRITICAL_AFTER:
        demo_state.mode = "incident"
        threshold = "critical"
    elif demo_state.submissions >= DEMO_DEGRADED_AFTER:
        demo_state.mode = "degraded"
        threshold = "degraded"
    else:
        threshold = "normal"
    emit("checkout_threshold_reached", submissions=demo_state.submissions, threshold=threshold, mode=demo_state.mode)


async def process_checkout(method: str = "GET"):
    started = time.perf_counter()
    status = "200"
    failure_reason = None
    try:
        if demo_state.mode == "offline":
            status = "503"
            failure_reason = "service_offline"
            ERRORS.labels("service_offline").inc()
            emit("checkout_unavailable", reason="service_offline")
            raise HTTPException(503, "checkout service unavailable")
        if demo_state.mode == "incident" and demo_state.submissions >= DEMO_CRITICAL_AFTER:
            status = "503"
            failure_reason = "critical_threshold"
            ERRORS.labels("critical_threshold").inc()
            emit("checkout_failed", reason="critical_threshold", submissions=demo_state.submissions)
            raise HTTPException(503, "checkout critical threshold reached")
        seconds = 0.08 if demo_state.mode == "normal" else DEGRADED_DELAY_SECONDS if demo_state.mode == "degraded" else 0.35
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
        if failure_reason is None:
            failure_reason = "pool_exhausted"
            ERRORS.labels("checkout_failed").inc()
            emit("checkout_failed", reason=failure_reason)
        raise
    finally:
        duration = time.perf_counter() - started
        LATENCY.labels("/checkout").observe(duration)
        REQUESTS.labels("/checkout", method, status).inc()


@app.get("/checkout")
async def checkout():
    return await process_checkout()


@app.post("/checkout")
async def submit_checkout(submission: CheckoutSubmission):
    register_submission()
    return await process_checkout("POST")


@app.get("/")
async def root():
    return FileResponse(UI_FILE)


@app.get("/checkout-api")
async def api_root():
    return {"service": "checkout-api", "links": ["/health", "/metrics", "/checkout", "/comprar", f"/{UI_PREFIX}"]}
