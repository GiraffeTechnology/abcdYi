import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.gpm_service import router
from src.gpm.api.auth import GPMAuthContext, require_gpm_auth
from src.gpm.api.deps import get_quote_guidance_service
from src.gpm.models.gpm_quote_guidance_packet import GPMQuoteGuidancePacket
from src.gpm.services.gpm_quote_guidance_api_service import GPMQuoteGuidanceApiService


def _dev_auth():
    return GPMAuthContext(tenant_id=None, operator_id=None, auth_method="dev_open")


def _mock_svc():
    store: dict[str, GPMQuoteGuidancePacket] = {}

    def generate(*, tenant_id, project_id, rfq_id, supplier_response_id,
                 evidence_ids, include_private_data, runtime_mode):
        p = GPMQuoteGuidancePacket.create(
            supplier_quote_position="at_benchmark",
            recommendation="accept",
            benchmark_range={"confidence": "high", "comparable_sample_count": 3},
            negotiation_points=[],
            buyer_quote_options=[{"option_id": "opt_accept", "label": "Accept"}],
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
    return svc


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api/gpm")
    svc = _mock_svc()
    app.dependency_overrides[get_quote_guidance_service] = lambda: svc
    app.dependency_overrides[require_gpm_auth] = _dev_auth
    return TestClient(app)


def test_healthz(client):
    r = client.get("/api/gpm/healthz")
    assert r.status_code == 200
    assert r.json()["human_approval_required"] is True


def test_capabilities(client):
    r = client.get("/api/gpm/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "F"
    assert data["constraints"]["human_approval_required"] is True
    assert data["constraints"]["no_automatic_business_actions"] is True


def test_create_quote_guidance_returns_pending_packet(client):
    r = client.post("/api/gpm/quote-guidance", json={
        "tenant_id": "t1", "rfq_id": "rfq1", "supplier_response_id": "sr1",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "ok"
    assert data["human_approval_required"] is True
    assert data["packet"]["approval_status"] == "pending"


def test_get_not_found(client):
    r = client.get("/api/gpm/quote-guidance/nonexistent-id")
    assert r.status_code == 404


def test_get_includes_operator_action_required(client):
    pid = client.post(
        "/api/gpm/quote-guidance", json={"rfq_id": "rfq-get"}
    ).json()["packet"]["packet_id"]
    r = client.get(f"/api/gpm/quote-guidance/{pid}")
    assert r.status_code == 200
    assert r.json()["operator_action_required"] is True


def test_approve_flow(client):
    create = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-approve"})
    pid = create.json()["packet"]["packet_id"]

    r = client.post(f"/api/gpm/quote-guidance/{pid}/approve", json={
        "operator_id": "op1", "approval_note": "looks good",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["dispatched"] is False
    assert data["approval_record"]["approval_status"] == "approved"


def test_double_approve_returns_409(client):
    create = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-dbl"})
    pid = create.json()["packet"]["packet_id"]
    client.post(f"/api/gpm/quote-guidance/{pid}/approve", json={"operator_id": "op1"})
    r = client.post(f"/api/gpm/quote-guidance/{pid}/approve", json={"operator_id": "op1"})
    assert r.status_code == 409


def test_reject_flow(client):
    create = client.post("/api/gpm/quote-guidance", json={"rfq_id": "rfq-reject"})
    pid = create.json()["packet"]["packet_id"]

    r = client.post(f"/api/gpm/quote-guidance/{pid}/reject", json={
        "operator_id": "op1", "approval_note": "too expensive",
    })
    assert r.status_code == 200
    assert r.json()["approval_record"]["approval_status"] == "rejected"
    assert r.json()["dispatched"] is False
