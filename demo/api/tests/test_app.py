import asyncio
import os

os.environ["APP_DB_NAME"] = "demo"
os.environ["APP_DB_USER"] = "demo"
os.environ["APP_DB_PASSWORD"] = "test-only"

from demo.api.app import DemoStateRequest, app, demo_state, health_payload, set_state


def test_health_stays_200_while_incident_is_degraded():
    demo_state.mode = "incident"
    payload = health_payload()
    assert payload["status"] == "ok"
    assert payload["http_status"] == 200
    assert payload["mode"] == "incident"


def test_health_becomes_degraded_only_after_pool_threshold():
    demo_state.mode = "incident"
    demo_state.pool_in_use = 5
    demo_state.pool_size = 5
    payload = health_payload()
    assert payload["status"] == "degraded"
    assert payload["http_status"] == 503


def test_expected_routes_exist():
    routes = {route.path for route in app.routes}
    assert {"/health", "/checkout", "/metrics", "/demo/state", "/demo/hold"} <= routes


def test_demo_state_accepts_json_request():
    response = asyncio.run(set_state(DemoStateRequest(mode="incident")))
    assert response["mode"] == "incident"
    assert response["health"]["mode"] == "incident"
