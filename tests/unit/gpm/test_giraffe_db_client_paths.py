"""Verify GiraffeDBClient uses correct /api/data/ prefixed paths.

These tests ensure the HTTP paths match giraffe-db's actual route layout:
- /healthz          (no prefix — health endpoint)
- /api/data/*       (all data routes)

A previous bug used bare paths (/schema-version, /gpm/context) that caused 404s.
"""
from __future__ import annotations

import json

import httpx
import pytest

from src.gpm.clients.giraffe_db_client import GiraffeDBClient


class _CapturingTransport(httpx.BaseTransport):
    """Records every request URL path; returns 200 with empty/minimal JSON."""

    def __init__(self) -> None:
        self.paths: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        # Return minimal valid responses for each method type
        if request.method == "GET":
            body = json.dumps({"status": "ok", "schema_version": "0.1.0"}).encode()
        else:
            body = json.dumps({"id": "ctx_001"}).encode()
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})


@pytest.fixture
def transport() -> _CapturingTransport:
    return _CapturingTransport()


@pytest.fixture
def client(transport: _CapturingTransport) -> GiraffeDBClient:
    return GiraffeDBClient(base_url="http://giraffe-db-test", transport=transport)


def test_healthz_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.healthz()
    assert transport.paths == ["/healthz"]


def test_schema_version_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.schema_version()
    assert transport.paths == ["/api/data/schema-version"]


def test_create_gpm_context_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.create_gpm_context({"tenant_id": "t1"})
    assert transport.paths == ["/api/data/gpm/context"]


def test_get_gpm_context_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.get_gpm_context("ctx-abc")
    assert transport.paths == ["/api/data/gpm/context/ctx-abc"]


def test_create_gltg_context_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.create_gltg_context({"tenant_id": "t1"})
    assert transport.paths == ["/api/data/gltg/context"]


def test_get_gltg_context_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.get_gltg_context("ctx-xyz")
    assert transport.paths == ["/api/data/gltg/context/ctx-xyz"]


def test_list_projects_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.list_projects()
    assert transport.paths == ["/api/data/projects"]


def test_list_rfqs_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.list_rfqs()
    assert transport.paths == ["/api/data/rfqs"]


def test_list_pricing_evidence_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.list_pricing_evidence()
    assert transport.paths == ["/api/data/gpm/pricing-evidence"]


def test_list_supplier_responses_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.list_supplier_responses()
    assert transport.paths == ["/api/data/supplier-responses"]


def test_list_lead_time_evidence_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.list_lead_time_evidence()
    assert transport.paths == ["/api/data/lead-time-evidence"]


def test_list_execution_events_path(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    client.list_execution_events()
    assert transport.paths == ["/api/data/execution-events"]


def test_no_bare_path_without_api_data_prefix(client: GiraffeDBClient, transport: _CapturingTransport) -> None:
    """Regression: no data route should use a bare path without /api/data/ prefix."""
    client.schema_version()
    client.create_gpm_context({"tenant_id": "t1"})
    client.get_gpm_context("x")
    client.list_projects()
    client.list_rfqs()
    client.list_pricing_evidence()

    for path in transport.paths:
        if path == "/healthz":
            continue  # health endpoint intentionally bare
        assert path.startswith("/api/data/"), (
            f"Expected /api/data/ prefix on data route, got: {path!r}"
        )
