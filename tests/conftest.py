import os as _os
import pytest as _pytest
from src.integrations import gltg_client as _gltg_client
from tests.gltg_fake import mock_transport as _gltg_mock_transport


@_pytest.fixture(autouse=True)
def _gltg_api_mock():
    if _os.environ.get("RUN_GLTG_INTEGRATION_TESTS") == "1":
        yield
        return
    _gltg_client.set_default_transport(_gltg_mock_transport())
    try:
        yield
    finally:
        _gltg_client.set_default_transport(None)


import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from api.main import app
from src.db.base import AsyncSessionLocal
from api.auth import hash_password


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def seed_user(db):
    from src.db.models.user import User
    from src.db.models.tenant import Tenant

    tenant = Tenant(name="Test Tenant", slug=f"test-{uuid.uuid4().hex[:8]}")
    db.add(tenant)
    await db.flush()

    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password=hash_password("testpassword"),
    )
    db.add(user)
    await db.commit()
    return {
        "email": user.email,
        "password": "testpassword",
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
    }


@pytest.fixture
async def auth_client(client, seed_user):
    resp = await client.post(
        "/api/auth/login",
        data={
            "username": seed_user["email"],
            "password": seed_user["password"],
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
async def seed_participant(auth_client):
    resp = await auth_client.post(
        "/api/participants",
        json={"name": "Seed Participant Co.", "country": "CN"},
    )
    assert resp.status_code == 201, f"Create participant failed: {resp.text}"
    return resp.json()


@pytest.fixture
async def seed_project(auth_client):
    resp = await auth_client.post(
        "/api/projects",
        json={"title": "Test Project"},
    )
    assert resp.status_code == 201, f"Create project failed: {resp.text}"
    return resp.json()


@pytest.fixture
async def seed_inquiry(auth_client, seed_project):
    resp = await auth_client.post(
        f"/api/projects/{seed_project['id']}/buyer-inquiries",
        json={"raw_text": "We need 10,000 white cotton shirts, FOB Shenzhen, delivery in 45 days."},
    )
    assert resp.status_code == 201, f"Create inquiry failed: {resp.text}"
    data = resp.json()
    data["project_id"] = seed_project["id"]
    return data


@pytest.fixture
async def seed_form(auth_client, seed_inquiry):
    resp = await auth_client.post(
        f"/api/projects/{seed_inquiry['project_id']}/dynamic-forms",
        json={"inquiry_id": seed_inquiry["id"]},
    )
    assert resp.status_code == 201, f"Create form failed: {resp.text}"
    data = resp.json()
    return {"form_id": str(data["form_id"]), "version_id": str(data["id"]), **data}


@pytest.fixture
async def seed_locked_form(auth_client, seed_form):
    resp = await auth_client.post(f"/api/dynamic-forms/{seed_form['form_id']}/lock")
    assert resp.status_code == 200, f"Lock form failed: {resp.text}"
    return seed_form


# ── Iter 4 fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
async def seed_project_with_form(auth_client):
    """A project with an inquiry and a dynamic form, returns project + form_version_id."""
    proj_resp = await auth_client.post("/api/projects", json={"title": "Matching Test Project"})
    assert proj_resp.status_code == 201
    project = proj_resp.json()

    inq_resp = await auth_client.post(
        f"/api/projects/{project['id']}/buyer-inquiries",
        json={"raw_text": "10,000 white cotton T-shirts, FOB Shenzhen, delivery in 60 days."},
    )
    assert inq_resp.status_code == 201
    inquiry = inq_resp.json()

    form_resp = await auth_client.post(
        f"/api/projects/{project['id']}/dynamic-forms",
        json={"inquiry_id": inquiry["id"]},
    )
    assert form_resp.status_code == 201
    form_data = form_resp.json()

    return {
        "id": project["id"],
        "form_version_id": str(form_data["id"]),
        "form_id": str(form_data["form_id"]),
    }


@pytest.fixture
async def seed_participants(auth_client):
    """Two participants with roles for matching tests."""
    p1_resp = await auth_client.post(
        "/api/participants",
        json={"name": "Shenzhen Garment Factory", "country": "CN"},
    )
    assert p1_resp.status_code == 201
    p1 = p1_resp.json()

    await auth_client.post(
        f"/api/participants/{p1['id']}/roles",
        json={"role_name": "MANUFACTURER"},
    )

    p2_resp = await auth_client.post(
        "/api/participants",
        json={"name": "Guangzhou Fabric Co.", "country": "CN"},
    )
    assert p2_resp.status_code == 201
    p2 = p2_resp.json()

    await auth_client.post(
        f"/api/participants/{p2['id']}/roles",
        json={"role_name": "FABRIC_SUPPLIER"},
    )

    return [p1, p2]


@pytest.fixture
async def seed_rfq(auth_client, seed_project_with_form, seed_participants):
    """An RFQ in PENDING_APPROVAL state with a linked ApprovalRequest."""
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/rfqs",
        json={
            "form_version_id": seed_project_with_form["form_version_id"],
            "recipient_participant_ids": [seed_participants[0]["id"]],
        },
    )
    assert resp.status_code == 201, f"Create RFQ failed: {resp.text}"
    data = resp.json()
    return {
        "id": data["rfq"]["id"],
        "approval_request_id": data["approval_request_id"],
        **data,
    }


@pytest.fixture
async def seed_sent_rfq(auth_client, seed_rfq):
    """An RFQ that has been approved and sent."""
    await auth_client.post(
        f"/api/approval-requests/{seed_rfq['approval_request_id']}/approve",
        json={"review_notes": "Approved for test"},
    )
    resp = await auth_client.post(
        f"/api/rfqs/{seed_rfq['id']}/send",
        json={"approval_id": seed_rfq["approval_request_id"]},
    )
    assert resp.status_code == 200, f"Send RFQ failed: {resp.text}"
    data = resp.json()
    data["id"] = data["id"]
    return data


# ── Iter 5 fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
async def seed_rfq_with_responses(auth_client, seed_sent_rfq, seed_participants):
    """A sent RFQ with at least one supplier response recorded."""
    await auth_client.post(
        f"/api/rfqs/{seed_sent_rfq['id']}/responses",
        json={
            "participant_id": seed_participants[0]["id"],
            "raw_response_text": (
                "We can supply 10,000 T-shirts. Unit price $8.50 USD, MOQ 500 pcs, "
                "fabric lead time 20 days, trim lead time 15 days, production time 25 days, "
                "QC time 5 days, logistics time 7 days, total lead time 57 days. "
                "Payment terms: 30% deposit, 70% before shipment. Trade terms: FOB Shenzhen. "
                "Capacity: 15000 pcs."
            ),
        },
    )
    return {
        "project_id": seed_sent_rfq.get("project_id", ""),
        "rfq_id": seed_sent_rfq["id"],
    }


@pytest.fixture
async def seed_decision_packet(auth_client, seed_rfq_with_responses, seed_project_with_form):
    """A decision packet in PENDING state."""
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/decision-packets",
        json={"rfq_id": seed_rfq_with_responses["rfq_id"]},
    )
    assert resp.status_code == 201, f"Create decision packet failed: {resp.text}"
    data = resp.json()
    return {
        "id": data["packet"]["id"],
        "project_id": seed_project_with_form["id"],
        "approval_request_id": data["approval_request_id"],
        "options": data["packet"]["options"],
        "recommended_option_id": data["packet"]["recommended_option_id"],
        **data["packet"],
    }


@pytest.fixture
async def seed_approved_packet(auth_client, seed_decision_packet):
    """A decision packet with an approved option."""
    packet_id = seed_decision_packet["id"]
    approval_id = seed_decision_packet["approval_request_id"]
    option_id = seed_decision_packet["options"][0]["id"]

    # Approve the ApprovalRequest first
    await auth_client.post(
        f"/api/approval-requests/{approval_id}/approve",
        json={"review_notes": "Approved for test"},
    )

    # Approve the option
    resp = await auth_client.post(
        f"/api/decision-packets/{packet_id}/approve-option",
        json={"option_id": option_id, "approval_id": approval_id},
    )
    assert resp.status_code == 200, f"Approve option failed: {resp.text}"
    return {
        **seed_decision_packet,
        "recommended_option_id": option_id,
        "approval_request_id": approval_id,
    }


@pytest.fixture
async def seed_draft_order(auth_client, seed_approved_packet):
    """A draft order created from an approved packet."""
    resp = await auth_client.post(
        f"/api/projects/{seed_approved_packet['project_id']}/orders/from-approved-option",
        json={
            "packet_id": seed_approved_packet["id"],
            "option_id": seed_approved_packet["recommended_option_id"],
            "approval_id": seed_approved_packet["approval_request_id"],
        },
    )
    assert resp.status_code == 201, f"Create order failed: {resp.text}"
    return resp.json()


@pytest.fixture
async def seed_confirmed_order(auth_client, seed_draft_order):
    """An order that has been confirmed and is IN_PRODUCTION."""
    resp = await auth_client.post(f"/api/orders/{seed_draft_order['id']}/confirm")
    assert resp.status_code == 200, f"Confirm order failed: {resp.text}"
    return resp.json()


# ── Iter 6 fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
async def seed_in_production_order(auth_client, seed_confirmed_order, db):
    """An IN_PRODUCTION order with its milestones accessible."""
    from sqlalchemy import select
    from src.db.models.production import Milestone
    result = await db.execute(
        select(Milestone).where(Milestone.order_id == seed_confirmed_order["id"])
    )
    milestones = result.scalars().all()
    return {
        **seed_confirmed_order,
        "milestones": [{"id": str(m.id), "milestone_type": m.milestone_type} for m in milestones],
    }


@pytest.fixture
async def seed_qc_order(auth_client, seed_confirmed_order):
    """An order in QC_PENDING state with a QC standard."""
    import uuid
    from datetime import datetime, timezone
    order_id = seed_confirmed_order["id"]
    form_version_id = seed_confirmed_order.get("locked_form_version_id")
    
    if form_version_id:
        await auth_client.post(
            f"/api/orders/{order_id}/qc-standards",
            json={"form_version_id": form_version_id},
        )

    # Manually set order to QC_PENDING by patching a milestone
    from src.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as db2:
        from src.db.models.order import Order
        order = await db2.get(Order, uuid.UUID(order_id))
        if order:
            order.status = "QC_PENDING"
            await db2.commit()

    return seed_confirmed_order


@pytest.fixture
async def seed_ready_to_ship_order(auth_client, seed_qc_order):
    """An order in READY_TO_SHIP state after passing QC."""
    resp = await auth_client.post(
        f"/api/orders/{seed_qc_order['id']}/qc-records",
        json={"label_compliance": True, "packaging_compliance": True},
    )
    return seed_qc_order


@pytest.fixture
async def seed_shipment(auth_client, seed_ready_to_ship_order):
    """A shipment created for a READY_TO_SHIP order."""
    from datetime import datetime, timezone
    resp = await auth_client.post(
        f"/api/orders/{seed_ready_to_ship_order['id']}/shipments",
        json={
            "carrier": "COSCO",
            "tracking_number": "COSU-TEST-001",
            "trade_term": "FOB",
            "origin": "Shenzhen",
            "destination": "Hamburg",
        },
    )
    assert resp.status_code == 201, f"Create shipment failed: {resp.text}"
    return resp.json()


@pytest.fixture
async def seed_delivered_order(auth_client, seed_shipment, seed_ready_to_ship_order):
    """An order in DELIVERED state."""
    from datetime import datetime, timezone
    await auth_client.post(
        f"/api/shipments/{seed_shipment['id']}/tracking-events",
        json={
            "event_type": "DELIVERED",
            "location": "Hamburg",
            "description": "Delivered to consignee",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return seed_ready_to_ship_order


@pytest.fixture
async def seed_delayed_order(auth_client, seed_in_production_order, db):
    """An order with a delayed milestone to trigger HIGH risk prediction."""
    from datetime import datetime, timezone, timedelta
    from src.db.models.production import Milestone
    import uuid
    
    milestones = seed_in_production_order.get("milestones", [])
    if milestones:
        ms_id = milestones[0]["id"]
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        await auth_client.patch(
            f"/api/milestones/{ms_id}",
            json={
                "status": "DELAYED",
                "predicted_date": future_date,
            },
        )
    return seed_in_production_order


@pytest.fixture
async def seed_expedite_alert(auth_client, seed_delayed_order):
    """Trigger a delay prediction that creates an expedite alert."""
    resp = await auth_client.post(
        f"/api/orders/{seed_delayed_order['id']}/run-delay-prediction"
    )
    return {
        "order_id": seed_delayed_order["id"],
        "monitoring_packet": resp.json(),
    }
