import asyncio
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import asyncpg
from fastapi import FastAPI, HTTPException, Request
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
POOL_ERRORS = Counter("checkout_db_pool_errors_total", "Database pool errors", ["reason"])
POOL_WAIT = Histogram("checkout_db_pool_wait_seconds", "Time spent waiting for a pool connection", buckets=(.001, .01, .05, .1, .25, .5, 1, 2, 5))
INCIDENT = Gauge("checkout_demo_incident", "1 while incident mode is enabled")
VALID_MODES = {"normal", "degraded", "incident", "offline", "progressive"}
DEMO_STAGE_SECONDS = float(os.getenv("DEMO_STAGE_SECONDS", "30"))
DEGRADED_DELAY_SECONDS = float(os.getenv("DEGRADED_DELAY_SECONDS", "2"))
DEMO_DEGRADED_AFTER = int(os.getenv("DEMO_DEGRADED_AFTER", "5"))
DEMO_CRITICAL_AFTER = int(os.getenv("DEMO_CRITICAL_AFTER", "12"))
DEMO_OFFLINE_AFTER = int(os.getenv("DEMO_OFFLINE_AFTER", "22"))
DB_ACQUIRE_TIMEOUT_SECONDS = float(os.getenv("DB_ACQUIRE_TIMEOUT_SECONDS", "2"))


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
hold_tasks: set[asyncio.Task] = set()


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


def trace_fields():
    if not trace:
        return {}
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return {}
    return {
        "trace_id": format(context.trace_id, "032x"),
        "span_id": format(context.span_id, "016x"),
    }


def emit(event: str, **fields):
    fields = {**trace_fields(), **fields}
    logger.info(json.dumps({"event": event, "service": "checkout-api", **fields}))


@app.middleware("http")
async def observe_request(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or secrets.token_hex(8)
    request.state.request_id = request_id
    started = time.perf_counter()
    status = 500
    error = None
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        error = type(exc).__name__
        raise
    finally:
        duration = time.perf_counter() - started
        path = request.url.path
        REQUESTS.labels(path, request.method, str(status)).inc()
        LATENCY.labels(path).observe(duration)
        emit(
            "http_request",
            request_id=request_id,
            endpoint=path,
            method=request.method,
            status=status,
            duration=round(duration, 6),
            error=error,
        )


def health_payload():
    pool_exhausted = demo_state.pool_in_use >= demo_state.pool_size
    critical = demo_state.mode == "incident" and (pool_exhausted or demo_state.submissions >= DEMO_CRITICAL_AFTER)
    degraded = demo_state.mode in {"degraded", "incident"} and (critical or demo_state.mode == "degraded")
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
        http_status = 200
        message = "pool capacity exhausted" if degraded else "basic process health; business latency may still be degraded"
    return {
        "status": status,
        "journey_status": "offline" if demo_state.mode == "offline" else "degraded" if degraded else "ok",
        "http_status": http_status,
        "mode": demo_state.mode,
        "pool_in_use": demo_state.pool_in_use,
        "pool_size": demo_state.pool_size,
        "waiting": demo_state.waiting,
        "pool_saturated": pool_exhausted,
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
    await cancel_hold_tasks()
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
            await start_incident_holds()


@app.post("/demo/state")
async def set_state(request: DemoStateRequest):
    global progression_task
    if request.mode not in VALID_MODES:
        raise HTTPException(400, "mode must be normal, degraded, incident, offline, or progressive")
    await cancel_progression()
    await cancel_hold_tasks()
    if request.mode == "progressive":
        demo_state.mode = "normal"
        demo_state.submissions = 0
        progression_task = asyncio.create_task(run_progression())
        emit("demo_progression_started", stage_seconds=DEMO_STAGE_SECONDS)
        return {"mode": request.mode, "health": health_payload(), "progression": True}
    demo_state.mode = request.mode
    if request.mode == "normal":
        demo_state.submissions = 0
    elif request.mode == "incident":
        await start_incident_holds()
    emit("demo_state_changed", mode=request.mode)
    return {"mode": request.mode, "health": health_payload()}


async def start_incident_holds():
    if not db_pool:
        return
    for _ in range(demo_state.pool_size):
        task = asyncio.create_task(hold_connection(demo_state.hold_seconds))
        hold_tasks.add(task)
        task.add_done_callback(hold_tasks.discard)


async def cancel_hold_tasks():
    tasks = list(hold_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    hold_tasks.clear()
    demo_state.waiting = 0
    demo_state.pool_in_use = 0
    POOL_IN_USE.set(0)
    POOL_WAITING.set(0)


async def hold_connection(seconds: float):
    if not db_pool:
        raise RuntimeError("database pool not ready")
    seconds = max(0.01, min(seconds, 60.0))
    acquired = False
    wait_started = time.perf_counter()
    demo_state.waiting += 1
    POOL_WAITING.set(demo_state.waiting)
    try:
        async with db_pool.acquire(timeout=DB_ACQUIRE_TIMEOUT_SECONDS) as conn:
            acquired = True
            demo_state.waiting = max(0, demo_state.waiting - 1)
            demo_state.pool_in_use += 1
            POOL_IN_USE.set(demo_state.pool_in_use)
            POOL_WAITING.set(demo_state.waiting)
            POOL_WAIT.observe(time.perf_counter() - wait_started)
            await conn.execute("SELECT pg_sleep($1)", seconds)
            return True
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        POOL_ERRORS.labels("timeout").inc()
        emit("pool_exhausted", pool_in_use=demo_state.pool_in_use, pool_size=demo_state.pool_size, waiting=demo_state.waiting)
        return False
    except Exception as exc:
        POOL_ERRORS.labels("database_error").inc()
        emit("pool_error", error=type(exc).__name__, detail=str(exc))
        return False
    finally:
        if not acquired:
            demo_state.waiting = max(0, demo_state.waiting - 1)
        else:
            demo_state.pool_in_use = max(0, demo_state.pool_in_use - 1)
        POOL_IN_USE.set(demo_state.pool_in_use)
        POOL_WAITING.set(demo_state.waiting)


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
    failure_reason = None
    try:
        if demo_state.mode == "offline":
            failure_reason = "service_offline"
            ERRORS.labels("service_offline").inc()
            emit("checkout_unavailable", reason="service_offline")
            raise HTTPException(503, "checkout service unavailable")
        if demo_state.mode == "incident" and demo_state.submissions >= DEMO_CRITICAL_AFTER:
            failure_reason = "critical_threshold"
            ERRORS.labels("critical_threshold").inc()
            emit("checkout_failed", reason="critical_threshold", submissions=demo_state.submissions)
            raise HTTPException(503, "checkout critical threshold reached")
        seconds = 0.08 if demo_state.mode == "normal" else DEGRADED_DELAY_SECONDS if demo_state.mode == "degraded" else 0.35
        if demo_state.mode == "incident":
            ok = await hold_connection(seconds)
            if not ok:
                failure_reason = "pool_exhausted"
                raise HTTPException(503, "checkout database pool exhausted")
        elif db_pool:
            demo_state.waiting += 1
            POOL_WAITING.set(demo_state.waiting)
            acquired = False
            wait_started = time.perf_counter()
            try:
                async with db_pool.acquire(timeout=DB_ACQUIRE_TIMEOUT_SECONDS) as conn:
                    acquired = True
                    demo_state.waiting = max(0, demo_state.waiting - 1)
                    demo_state.pool_in_use += 1
                    POOL_IN_USE.set(demo_state.pool_in_use)
                    POOL_WAITING.set(demo_state.waiting)
                    POOL_WAIT.observe(time.perf_counter() - wait_started)
                    await conn.execute("SELECT 1")
            except asyncio.TimeoutError:
                failure_reason = "pool_exhausted"
                POOL_ERRORS.labels("timeout").inc()
                raise HTTPException(503, "checkout database pool exhausted")
            finally:
                if not acquired:
                    demo_state.waiting = max(0, demo_state.waiting - 1)
                else:
                    demo_state.pool_in_use = max(0, demo_state.pool_in_use - 1)
                POOL_IN_USE.set(demo_state.pool_in_use)
                POOL_WAITING.set(demo_state.waiting)
            if demo_state.mode == "degraded":
                await asyncio.sleep(DEGRADED_DELAY_SECONDS)
        return {"status": "confirmed", "mode": demo_state.mode}
    except HTTPException:
        if failure_reason is None:
            failure_reason = "pool_exhausted"
            ERRORS.labels("checkout_failed").inc()
            emit("checkout_failed", reason=failure_reason)
        raise
    except Exception as exc:
        ERRORS.labels("internal_error").inc()
        emit("checkout_failed", reason="internal_error", error=type(exc).__name__)
        raise HTTPException(500, "checkout failed") from exc


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
