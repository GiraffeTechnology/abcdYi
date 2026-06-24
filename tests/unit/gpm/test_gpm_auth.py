"""Tests for GPM API authentication, tenant validation, and retriever init errors."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.gpm_service import router
from src.gpm.api.deps import get_quote_guidance_service
from src.gpm.models.gpm_quote_guidance_packet import GPMQuoteGuidancePacket
from src.gpm.services.gpm_quote_guidance_api_service import GPMQuoteGuidanceApiService

_KEY = "test-gpm-api-key-abc123"


def _mock_svc():
    store: dict[str, GPMQuoteGuidancePacket] = {}

    def generate(*, tenant_id, **kwargs):
        p = GPMQuoteGuidancePacket.create(
            tenant_id=tenant_id,
            supplier_quote_position="at_benchmark",
            recommendation="accept",
            benchmark_range={},
            negotiation_points=[],
            buyer_quote_options=[],
            runtime_profile="ci",
            runtime_mode="mock",
            context_retriever="mock",
            data_mode="public",
        )
        store[p.packet_id] = p
        return {"status": "ok", "packet": p, "error": None, "operator_action_required": True}

    svc = object.__new__(GPMQuoteGuidanceApiService)
    svc.generate_quote_guidance = generate
    svc.get_packet = lambda pid: store.get(pid)
    return svc, store


@pytest.fixture
def app_with_key(monkeypatch):
    monkeypatch.setenv("GPM_API_KEY", _KEY)
    svc, _ = _mock_svc()
    a = FastAPI()
    a.include_router(router, prefix="/api/gpm")
    a.dependency_overrides[get_quote_guidance_service] = lambda: svc
    return TestClient(a)


@pytest.fixture
def app_open():
    """Dev-open mode: no GPM_API_KEY set."""
    svc, _ = _mock_svc()
    a = FastAPI()
    a.include_router(router, prefix="/api/gpm")
    a.dependency_overrides[get_quote_guidance_service] = lambda: svc
    return TestClient(a)


# --- API key enforcement ---

def test_missing_key_returns_401(app_with_key):
    r = app_with_key.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-001"})
    assert r.status_code == 401


def test_wrong_key_returns_401(app_with_key):
    r = app_with_key.post(
        "/api/gpm/quote-guidance",
        json={"rfq_id": "rfq-001"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert r.status_code == 401


def test_correct_key_accepted(app_with_key):
    r = app_with_key.post(
        "/api/gpm/quote-guidance",
        json={"rfq_id": "rfq-001"},
        headers={"Authorization": f"Bearer {_KEY}"},
    )
    assert r.status_code == 201


def test_unauthenticated_approve_returns_401(app_with_key):
    pid = app_with_key.post(
        "/api/gpm/quote-guidance",
        json={"rfq_id": "rfq-002"},
        headers={"Authorization": f"Bearer {_KEY}"},
    ).json()["packet"]["packet_id"]
    r = app_with_key.post(
        f"/api/gpm/quote-guidance/{pid}/approve",
        json={"operator_id": "op1"},
    )
    assert r.status_code == 401


def test_unauthenticated_reject_returns_401(app_with_key):
    pid = app_with_key.post(
        "/api/gpm/quote-guidance",
        json={"rfq_id": "rfq-003"},
        headers={"Authorization": f"Bearer {_KEY}"},
    ).json()["packet"]["packet_id"]
    r = app_with_key.post(
        f"/api/gpm/quote-guidance/{pid}/reject",
        json={"operator_id": "op1"},
    )
    assert r.status_code == 401


def test_unauthenticated_get_returns_401(app_with_key):
    r = app_with_key.get("/api/gpm/quote-guidance/any-id")
    assert r.status_code == 401


def test_dev_open_mode_passes_without_key(app_open):
    r = app_open.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-dev"})
    assert r.status_code == 201


# --- Public endpoints have no auth requirement ---

def test_healthz_public(app_with_key):
    assert app_with_key.get("/api/gpm/healthz").status_code == 200


def test_capabilities_public(app_with_key):
    assert app_with_key.get("/api/gpm/capabilities").status_code == 200


# --- Tenant validation ---

def test_matching_tenant_accepted(app_open):
    r = app_open.post(
        "/api/gpm/quote-guidance",
        json={"tenant_id": "tenant-A", "rfq_id": "rfq-t1"},
        headers={"X-Giraffe-Tenant-ID": "tenant-A"},
    )
    assert r.status_code == 201
    assert r.json()["packet"]["tenant_id"] == "tenant-A"


def test_tenant_id_mismatch_returns_403(app_open):
    r = app_open.post(
        "/api/gpm/quote-guidance",
        json={"tenant_id": "tenant-EVIL", "rfq_id": "rfq-t2"},
        headers={"X-Giraffe-Tenant-ID": "tenant-LEGIT"},
    )
    assert r.status_code == 403
    assert "mismatch" in r.json()["detail"]["error"]


def test_cross_tenant_get_returns_403(app_open):
    pid = app_open.post(
        "/api/gpm/quote-guidance",
        json={"rfq_id": "rfq-t3"},
        headers={"X-Giraffe-Tenant-ID": "tenant-A"},
    ).json()["packet"]["packet_id"]
    r = app_open.get(
        f"/api/gpm/quote-guidance/{pid}",
        headers={"X-Giraffe-Tenant-ID": "tenant-B"},
    )
    assert r.status_code == 403


def test_cross_tenant_approve_returns_403(app_open):
    pid = app_open.post(
        "/api/gpm/quote-guidance",
        json={"rfq_id": "rfq-t4"},
        headers={"X-Giraffe-Tenant-ID": "tenant-A"},
    ).json()["packet"]["packet_id"]
    r = app_open.post(
        f"/api/gpm/quote-guidance/{pid}/approve",
        json={"operator_id": "evil-op"},
        headers={"X-Giraffe-Tenant-ID": "tenant-B"},
    )
    assert r.status_code == 403


# --- GET includes operator_action_required ---

def test_get_includes_operator_action_required(app_open):
    pid = app_open.post(
        "/api/gpm/quote-guidance", json={"rfq_id": "rfq-oar"}
    ).json()["packet"]["packet_id"]
    r = app_open.get(f"/api/gpm/quote-guidance/{pid}")
    assert r.status_code == 200
    assert r.json()["operator_action_required"] is True


# --- Missing retriever URL → structured 502 ---

def test_missing_retriever_url_returns_structured_502(monkeypatch):
    from src.gpm.api import deps

    deps._try_build_service.cache_clear()
    deps.get_runtime_config.cache_clear()

    monkeypatch.setenv("GPM_CONTEXT_RETRIEVER", "giraffe_db")
    monkeypatch.delenv("GPM_GIRAFFE_DB_BASE_URL", raising=False)

    a = FastAPI()
    a.include_router(router, prefix="/api/gpm")
    client = TestClient(a)

    try:
        r = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-err"})
        assert r.status_code == 502
        detail = r.json()["detail"]
        assert detail["status"] == "context_unavailable"
        assert detail["operator_action_required"] is True
        assert "error" in detail
    finally:
        deps._try_build_service.cache_clear()
        deps.get_runtime_config.cache_clear()
