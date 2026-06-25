"""Validate the API contract that the OpenClaw TypeScript skill depends on."""
import os

os.environ["GPM_CONTEXT_RETRIEVER"] = "mock"
os.environ["GPM_RUNTIME_PROFILE"] = "ci"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module", autouse=True)
def _reset_deps_cache():
    # get_quote_guidance_service is a plain dependency; the lru_cache is on _try_build_service
    from src.gpm.api.deps import _try_build_service, get_runtime_config
    _try_build_service.cache_clear()
    get_runtime_config.cache_clear()
    yield
    _try_build_service.cache_clear()
    get_runtime_config.cache_clear()


@pytest.fixture(scope="module")
def client(_reset_deps_cache):
    from api.main import app
    return TestClient(app)


def test_skill_create_request_shape(client):
    r = client.post("/api/gpm/quote-guidance", json={
        "tenant_id": "openclaw-tenant",
        "operator_id": "openclaw-op",
        "rfq_id": "rfq-skill-001",
        "supplier_response_id": "sr-skill-001",
        "include_private_data": True,
        "request_context": {"source": "openclaw"},
    })
    assert r.status_code == 201
    data = r.json()
    assert data["packet"]["human_approval_required"] is True
    assert data["packet"]["approval_status"] == "pending"
    assert "operator_action_required" in data


def test_skill_approval_contract(client):
    r = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-skill-002"})
    pid = r.json()["packet"]["packet_id"]

    approve_r = client.post(f"/api/gpm/quote-guidance/{pid}/approve", json={
        "operator_id": "openclaw-op",
        "approval_note": "Skill smoke approval",
        "selected_option_id": "opt_accept",
    })
    assert approve_r.status_code == 200
    rec = approve_r.json()["approval_record"]
    assert rec["dispatched"] is False
    assert "No external action" in rec["dispatch_note"]


def test_skill_never_dispatches_automatically(client):
    r = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-skill-003"})
    pid = r.json()["packet"]["packet_id"]

    approve_r = client.post(f"/api/gpm/quote-guidance/{pid}/approve",
                            json={"operator_id": "op"})
    assert approve_r.json()["dispatched"] is False


def test_packet_has_no_order_dispatch_fields(client):
    r = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-skill-004"})
    packet_keys = set(r.json()["packet"].keys())
    banned = {"order_id", "payment_id", "dispatch_ref", "cart_id"}
    assert not packet_keys & banned
