import asyncio
import os

os.environ["APP_DB_NAME"] = "demo"
os.environ["APP_DB_USER"] = "demo"
os.environ["APP_DB_PASSWORD"] = "test-only"

from demo.api.app import DemoStateRequest, app, demo_state, health_payload, register_submission, set_state


def reset_state():
    demo_state.mode = "normal"
    demo_state.pool_in_use = 0
    demo_state.waiting = 0
    demo_state.submissions = 0


def test_health_stays_200_while_incident_is_degraded():
    reset_state()
    demo_state.mode = "incident"
    payload = health_payload()
    assert payload["status"] == "ok"
    assert payload["http_status"] == 200
    assert payload["mode"] == "incident"


def test_health_becomes_degraded_only_after_pool_threshold():
    reset_state()
    demo_state.mode = "incident"
    demo_state.pool_in_use = 5
    demo_state.pool_size = 5
    payload = health_payload()
    assert payload["status"] == "degraded"
    assert payload["http_status"] == 503


def test_expected_routes_exist():
    routes = {route.path for route in app.routes}
    assert {"/", "/comprar", "/health", "/checkout", "/metrics", "/demo/state", "/demo/hold"} <= routes


def test_demo_state_accepts_json_request():
    reset_state()
    response = asyncio.run(set_state(DemoStateRequest(mode="incident")))
    assert response["mode"] == "incident"
    assert response["health"]["mode"] == "incident"


def test_degraded_health_is_available_but_explicit():
    reset_state()
    demo_state.mode = "degraded"
    payload = health_payload()
    assert payload["status"] == "degraded"
    assert payload["http_status"] == 200


def test_offline_health_is_unavailable():
    reset_state()
    demo_state.mode = "offline"
    payload = health_payload()
    assert payload["status"] == "offline"
    assert payload["http_status"] == 503


def test_demo_state_accepts_progressive_mode():
    reset_state()
    response = asyncio.run(set_state(DemoStateRequest(mode="progressive")))
    assert response["mode"] == "progressive"
    assert response["progression"] is True


def test_public_submission_thresholds_progress_to_offline():
    reset_state()
    for _ in range(4):
        register_submission()
    assert demo_state.mode == "normal"
    register_submission()
    assert demo_state.mode == "degraded"
    for _ in range(7):
        register_submission()
    assert demo_state.mode == "incident"
    for _ in range(10):
        register_submission()
    assert demo_state.mode == "offline"
    assert demo_state.submissions == 22
