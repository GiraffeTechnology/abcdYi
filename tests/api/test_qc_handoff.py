"""The natural production-to-QC handoff stays authenticated, scoped and durable."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


async def test_request_qc_persists_and_audits(auth_client, seed_confirmed_order, seed_user):
    order_id = seed_confirmed_order["id"]
    response = await auth_client.post(f"/api/orders/{order_id}/request-qc")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "QC_PENDING"

    # A new client/session recovers the state without the original conversation.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as resumed:
        resumed.headers["Authorization"] = auth_client.headers["Authorization"]
        order = await resumed.get(f"/api/orders/{order_id}")
        assert order.status_code == 200
        assert order.json()["status"] == "QC_PENDING"
        events = await resumed.get(f"/api/execution-graph/orders/{order_id}")
        handoffs = [e for e in events.json() if e["event_type"] == "QC_REQUESTED"]
        assert len(handoffs) == 1
        event = handoffs[0]
        assert event["triggered_by_user_id"] == seed_user["user_id"]
        assert event["tenant_id"] == seed_user["tenant_id"]
        assert event["project_id"] == seed_confirmed_order["project_id"]
        assert event["payload"] == {
            "order_id": order_id, "previous_status": "IN_PRODUCTION", "status": "QC_PENDING",
        }

    repeated = await auth_client.post(f"/api/orders/{order_id}/request-qc")
    assert repeated.status_code == 409
    events = await auth_client.get(f"/api/execution-graph/orders/{order_id}")
    assert sum(e["event_type"] == "QC_REQUESTED" for e in events.json()) == 1


async def test_request_qc_rejects_unconfirmed_order(auth_client, seed_draft_order):
    order_id = seed_draft_order["id"]
    response = await auth_client.post(f"/api/orders/{order_id}/request-qc")
    assert response.status_code == 409
    order = await auth_client.get(f"/api/orders/{order_id}")
    assert order.json()["status"] == "DRAFT_FROM_APPROVED_QUOTE"


async def test_request_qc_requires_auth_and_hides_other_tenants(auth_client, seed_confirmed_order, db):
    from api.auth import hash_password
    from src.db.models.tenant import Tenant
    from src.db.models.user import User

    tenant = Tenant(name="Other QC tenant", slug=f"qc-{uuid.uuid4().hex}")
    db.add(tenant)
    await db.flush()
    email = f"qc-other-{uuid.uuid4().hex}@example.com"
    db.add(User(tenant_id=tenant.id, email=email, hashed_password=hash_password("TestPassword123!")))
    await db.commit()
    order_id = seed_confirmed_order["id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        response = await other.post(f"/api/orders/{order_id}/request-qc")
        assert response.status_code == 401
        response = await other.post("/api/auth/login", data={"username": email, "password": "TestPassword123!"})
        assert response.status_code == 200
        other.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        response = await other.post(f"/api/orders/{order_id}/request-qc")
        assert response.status_code == 404
        missing = await other.post(f"/api/orders/{uuid.uuid4()}/request-qc")
        assert missing.status_code == 404
    order = await auth_client.get(f"/api/orders/{order_id}")
    assert order.json()["status"] == "IN_PRODUCTION"


async def test_audit_failure_does_not_persist_qc_transition(auth_client, seed_confirmed_order, monkeypatch):
    async def failed_write(**kwargs):
        raise RuntimeError("Synthetic audit write failure")

    monkeypatch.setattr("src.orders.service.emit_event", failed_write)
    order_id = seed_confirmed_order["id"]
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test",
        headers={"Authorization": auth_client.headers["Authorization"]},
    ) as failing:
        response = await failing.post(f"/api/orders/{order_id}/request-qc")
        assert response.status_code == 500
    order = await auth_client.get(f"/api/orders/{order_id}")
    assert order.json()["status"] == "IN_PRODUCTION"


@pytest.mark.parametrize("passed", [True, False])
async def test_qc_result_preserves_shipping_gate(auth_client, seed_confirmed_order, passed):
    order_id = seed_confirmed_order["id"]
    assert (await auth_client.post(f"/api/orders/{order_id}/request-qc")).status_code == 200
    response = await auth_client.post(
        f"/api/orders/{order_id}/qc-records",
        json={"label_compliance": passed, "packaging_compliance": passed},
    )
    assert response.status_code == 201
    order = await auth_client.get(f"/api/orders/{order_id}")
    assert order.json()["status"] == ("READY_TO_SHIP" if passed else "QC_FAILED")
    response = await auth_client.post(f"/api/orders/{order_id}/request-qc")
    assert response.status_code == 409
    if not passed:
        response = await auth_client.post(f"/api/orders/{order_id}/shipments", json={"carrier": "Synthetic carrier"})
        assert response.status_code == 409
