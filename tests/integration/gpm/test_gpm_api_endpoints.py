"""Integration tests: full FastAPI app with mock LLM runtime."""
import os

os.environ["GPM_CONTEXT_RETRIEVER"] = "mock"
os.environ["GPM_RUNTIME_PROFILE"] = "ci"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module", autouse=True)
def _reset_deps_cache():
    from src.gpm.api.deps import get_runtime_config, _try_build_service
    _saved_key = os.environ.pop("GPM_API_KEY", None)
    _try_build_service.cache_clear()
    get_runtime_config.cache_clear()
    yield
    _try_build_service.cache_clear()
    get_runtime_config.cache_clear()
    if _saved_key is not None:
        os.environ["GPM_API_KEY"] = _saved_key


@pytest.fixture(scope="module")
def client(_reset_deps_cache):
    from api.main import app
    return TestClient(app)


def test_gpm_healthz(client):
    r = client.get("/api/gpm/healthz")
    assert r.status_code == 200
    assert r.json()["human_approval_required"] is True


def test_gpm_capabilities(client):
    r = client.get("/api/gpm/capabilities")
    assert r.status_code == 200
    assert "POST /api/gpm/quote-guidance" in r.json()["endpoints"]


def test_full_quote_guidance_flow(client):
    r = client.post("/api/gpm/quote-guidance", json={
        "tenant_id": "t-integration",
        "project_id": "p-001",
        "rfq_id": "rfq-001",
        "supplier_response_id": "sr-001",
        "include_private_data": False,
    })
    assert r.status_code == 201, r.text
    packet = r.json()["packet"]
    assert packet["human_approval_required"] is True
    assert packet["approval_status"] == "pending"
    pid = packet["packet_id"]

    get_r = client.get(f"/api/gpm/quote-guidance/{pid}")
    assert get_r.status_code == 200
    assert get_r.json()["packet"]["packet_id"] == pid
    assert get_r.json()["operator_action_required"] is True

    approve_r = client.post(f"/api/gpm/quote-guidance/{pid}/approve", json={
        "operator_id": "op-integration",
        "approval_note": "Integration test approval",
    })
    assert approve_r.status_code == 200
    assert approve_r.json()["approval_record"]["approval_status"] == "approved"
    assert approve_r.json()["dispatched"] is False

    dbl = client.post(
        f"/api/gpm/quote-guidance/{pid}/approve", json={"operator_id": "op-integration"}
    )
    assert dbl.status_code == 409


def test_reject_flow(client):
    r = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-002"})
    assert r.status_code == 201
    pid = r.json()["packet"]["packet_id"]

    rej = client.post(f"/api/gpm/quote-guidance/{pid}/reject", json={
        "operator_id": "op-integration", "approval_note": "Price too high",
    })
    assert rej.status_code == 200
    assert rej.json()["approval_record"]["approval_status"] == "rejected"
    assert rej.json()["dispatched"] is False
