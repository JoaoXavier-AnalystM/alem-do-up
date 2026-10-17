"""Repository-level contracts for the observability laboratory.

These tests intentionally inspect repository artifacts instead of importing the
application. They keep documentation, Compose inputs, dashboards, and runtime
configuration aligned without changing those artifacts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover - reported by the YAML contract test
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    ROOT / "README.md",
    ROOT / "docs" / "ARCHITECTURE.md",
    ROOT / "docs" / "PRESENTATION_CHECKLIST.md",
)
MAIN_COMPOSE = ROOT / "docker-compose.yml"
MAIN_ENV = ROOT / ".env.example"
GRAFANA_DATASOURCES = ROOT / "observability" / "grafana" / "provisioning" / "datasources" / "datasources.yml"
DASHBOARD_DIR = ROOT / "observability" / "grafana" / "dashboards"

DOCUMENTED_REFERENCES = {
    ROOT / "README.md": (
        ".env.example",
        "docker-compose.yml",
        "scripts/up.sh",
        "scripts/smoke.sh",
        "scripts/normal.sh",
        "scripts/incident.sh",
        "scripts/load.sh",
        "scripts/recover.sh",
        "scripts/validate-repository.sh",
        "docs/ARCHITECTURE.md",
        "opendockwatch/",
    ),
    ROOT / "docs" / "ARCHITECTURE.md": (
        "docker-compose.yml",
        "scripts/incident.sh",
        "scripts/load.sh",
        "scripts/recover.sh",
        ".env.example",
    ),
    ROOT / "docs" / "PRESENTATION_CHECKLIST.md": (
        ".env.example",
        "scripts/up.sh",
        "scripts/smoke.sh",
        "scripts/normal.sh",
        "scripts/incident.sh",
        "scripts/load.sh",
        "scripts/recover.sh",
        "scripts/gradual.sh",
        "scripts/validate-repository.sh",
        "load/k6.js",
        "observability/grafana/dashboards/k6-load.json",
        "observability/grafana/dashboards/DIA D/01-servidor-ok.json",
        "observability/grafana/dashboards/DIA D/02-banco-api-ok.json",
        "observability/grafana/dashboards/DIA D/03-visao-operacional.json",
        "observability/grafana/dashboards/DIA D/04-traces-logs-metricas-erros.json",
    ),
}

EXPECTED_COMPOSE_ENV = {
    "docker-compose.yml": ROOT / ".env.example",
    "opendockwatch/docker-compose.yml": ROOT / "opendockwatch" / ".env.example",
    "cloudflare/docker-compose.yml": ROOT / "cloudflare" / ".env.example",
}

EXPECTED_APP_METRICS = {
    "checkout_http_request_duration_seconds",
    "checkout_http_request_duration_seconds_bucket",
    "checkout_http_requests_total",
    "checkout_errors_total",
    "checkout_db_pool_in_use",
    "checkout_db_pool_waiting",
    "checkout_db_pool_size",
    "checkout_db_pool_errors_total",
    "checkout_db_pool_wait_seconds",
    "checkout_db_pool_wait_seconds_bucket",
    "checkout_demo_incident",
}
EXPECTED_K6_METRICS = {
    "k6_http_reqs_total",
    "k6_http_req_failed_rate",
    "k6_vus",
    "k6_checks_rate",
    "k6_http_req_duration_p95",
    "k6_http_req_duration_p50",
    "k6_http_req_duration_avg",
    "k6_iteration_duration_p95",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_env(path: Path) -> set[str]:
    return {
        match.group(1)
        for line in read(path).splitlines()
        if (match := re.match(r"^([A-Z][A-Z0-9_]*)=", line.strip()))
    }


def yaml_paths() -> list[Path]:
    roots = (ROOT / ".github", ROOT / "cloudflare", ROOT / "observability", ROOT / "opendockwatch")
    paths = [ROOT / "docker-compose.yml"]
    for directory in roots:
        paths.extend(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}
        )
    return sorted(set(paths))


def json_paths() -> list[Path]:
    roots = (ROOT / ".github", ROOT / "cloudflare", ROOT / "observability", ROOT / "opendockwatch")
    paths: list[Path] = []
    for directory in roots:
        paths.extend(path for path in directory.rglob("*.json") if path.is_file())
    return sorted(set(paths))


def walk_values(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


@pytest.mark.parametrize("document, references", DOCUMENTED_REFERENCES.items())
def test_documented_repository_references_exist(document: Path, references: tuple[str, ...]):
    content = read(document)
    missing = [reference for reference in references if not (ROOT / reference.rstrip("/")).exists()]
    undocumented = [reference for reference in references if reference not in content]
    assert not missing, f"missing repository references in {document}: {missing}"
    assert not undocumented, f"references not documented in {document}: {undocumented}"


def test_json_files_are_parseable():
    errors = []
    for path in json_paths():
        try:
            json.loads(read(path))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    assert not errors, "invalid JSON:\n" + "\n".join(errors)


def test_yaml_files_are_parseable():
    if yaml is None:
        pytest.fail("PyYAML is required to validate repository YAML files")
    errors = []
    for path in yaml_paths():
        try:
            yaml.safe_load(read(path))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    assert not errors, "invalid YAML:\n" + "\n".join(errors)


def test_compose_interpolations_are_declared_in_adjacent_env_examples():
    missing = []
    for compose_name, env_path in EXPECTED_COMPOSE_ENV.items():
        compose_path = ROOT / compose_name
        variables = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)(?::-[^}]*)?\}", read(compose_path)))
        missing.extend(f"{compose_name}: {name}" for name in sorted(variables - parse_env(env_path)))
    assert not missing, "Compose variables absent from .env.example:\n" + "\n".join(missing)


def test_main_env_ui_prefix_is_forwarded_by_compose():
    env_keys = parse_env(MAIN_ENV)
    compose = read(MAIN_COMPOSE)
    docs = "\n".join(read(path) for path in DOCS)
    assert "APP_UI_PREFIX" in env_keys
    assert "APP_UI_PREFIX" in compose
    assert "APP_UI_PREFIX" in docs
    assert "prefixo" in docs.lower()


def test_repository_validation_script_is_safe_and_self_contained():
    path = ROOT / "scripts" / "validate-repository.sh"
    assert path.exists()
    content = read(path)
    assert content.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in content
    assert "tests/test_repository_contracts.py" in content
    assert "docker compose" in content


def test_grafana_dashboard_datasource_uids_are_provisioned():
    if yaml is None:
        pytest.fail("PyYAML is required to validate Grafana datasource UIDs")
    provisioned = yaml.safe_load(read(GRAFANA_DATASOURCES))
    allowed_uids = {item["uid"] for item in provisioned["datasources"]}
    unknown = []
    for path in sorted(DASHBOARD_DIR.rglob("*.json")):
        dashboard = json.loads(read(path))
        for key, value in walk_values(dashboard):
            if key == "datasource" and isinstance(value, dict) and value.get("uid") not in allowed_uids:
                unknown.append(f"{path.relative_to(ROOT)}: {value.get('uid')}")
    assert not unknown, "dashboard datasource UIDs not provisioned:\n" + "\n".join(unknown)


def test_grafana_dashboard_uids_are_unique_when_present():
    uids: dict[str, Path] = {}
    duplicates = []
    for path in sorted(DASHBOARD_DIR.rglob("*.json")):
        dashboard = json.loads(read(path))
        uid = dashboard.get("uid")
        if not uid:
            continue
        if uid in uids:
            duplicates.append(f"{uid}: {uids[uid].relative_to(ROOT)} and {path.relative_to(ROOT)}")
        uids[uid] = path
    assert not duplicates, "duplicate dashboard UIDs:\n" + "\n".join(duplicates)


def test_grafana_prometheus_queries_use_repository_metrics():
    known = EXPECTED_APP_METRICS | EXPECTED_K6_METRICS
    unknown = []
    for path in sorted(DASHBOARD_DIR.rglob("*.json")):
        dashboard = json.loads(read(path))
        for key, value in walk_values(dashboard):
            if key != "expr" or not isinstance(value, str) or "container=" in value:
                continue
            metrics = set(re.findall(r"\b(?:checkout|k6)_[a-zA-Z0-9_:]+", value))
            unknown.extend(f"{path.relative_to(ROOT)}: {metric}" for metric in sorted(metrics - known))
    assert not unknown, "dashboard queries reference unknown metrics:\n" + "\n".join(unknown)


def test_grafana_loki_queries_match_emitted_pool_event():
    queries = []
    for path in sorted(DASHBOARD_DIR.rglob("*.json")):
        dashboard = json.loads(read(path))
        for key, value in walk_values(dashboard):
            if key == "expr" and isinstance(value, str) and "container=\"api-up\"" in value:
                queries.append((path, value))
    assert queries
    assert any("pool_exhausted" in query and "db_pool_exhausted" not in query for _, query in queries)
    assert all("db_pool_exhausted" not in query for _, query in queries)


def test_docs_state_local_observability_contract():
    readme = read(ROOT / "README.md")
    architecture = read(ROOT / "docs" / "ARCHITECTURE.md")
    checklist = read(ROOT / "docs" / "PRESENTATION_CHECKLIST.md")
    joined = "\n".join((readme, architecture, checklist))
    for term in ("/health", "/checkout", "pool", "incident", "load", "recover", "Docker"):
        assert term in joined, f"documentation omits contract term: {term}"
    for port in ("5055", "3000", "9090", "16686", "3001"):
        assert port in joined, f"documentation omits local port: {port}"
    assert "200" in architecture
    assert "503" in architecture
