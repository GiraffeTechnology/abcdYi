"""Integration tests for Giraffe JP web dialog and email communication API."""
import pytest
import uuid


@pytest.mark.asyncio
async def test_create_conversation_thread(auth_client):
    resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER", "subject": "Order enquiry"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["party_type"] == "CUSTOMER"
    assert data["subject"] == "Order enquiry"
    assert data["status"] == "OPEN"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(auth_client):
    await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "SUPPLIER"},
    )
    resp = await auth_client.get("/api/giraffe-jp/conversations")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_conversation_thread(auth_client):
    create_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "MODEL_PARTNER", "thread_type": "FIT_REVIEW"},
    )
    thread_id = create_resp.json()["id"]
    resp = await auth_client.get(f"/api/giraffe-jp/conversations/{thread_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == thread_id


@pytest.mark.asyncio
async def test_get_conversation_not_found(auth_client):
    resp = await auth_client.get(f"/api/giraffe-jp/conversations/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_record_inbound_message(auth_client):
    create_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER"},
    )
    thread_id = create_resp.json()["id"]

    resp = await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/messages/inbound",
        json={"body": "Hello, I have a question about my order.", "sender_ref": "customer@example.com"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["direction"] == "INBOUND"
    assert data["body"] == "Hello, I have a question about my order."
    assert data["thread_id"] == thread_id


@pytest.mark.asyncio
async def test_create_outbound_draft_unknown_category_pending(auth_client):
    """Spec rule 7/8: unknown category -> PENDING_HUMAN_CONFIRMATION (never AUTO_SENT)."""
    create_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER"},
    )
    thread_id = create_resp.json()["id"]

    resp = await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts",
        json={"category_id": "UNKNOWN_CAT_XYZ", "body": "Some message body."},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["approval_status"] == "PENDING_HUMAN_CONFIRMATION"


@pytest.mark.asyncio
async def test_create_outbound_draft_known_auto_send_category(auth_client):
    """After seeding, CUST_ORDER_CONFIRMATION (auto_send=True) -> AUTO_SENT."""
    await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")

    create_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER"},
    )
    thread_id = create_resp.json()["id"]

    resp = await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts",
        json={"category_id": "CUST_ORDER_CONFIRMATION", "body": "Your order is confirmed."},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["approval_status"] == "AUTO_SENT"


@pytest.mark.asyncio
async def test_create_outbound_draft_manual_category_pending(auth_client):
    """CUST_PAYMENT_REMINDER (auto_send=False) -> PENDING_HUMAN_CONFIRMATION."""
    await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")

    create_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER"},
    )
    thread_id = create_resp.json()["id"]

    resp = await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts",
        json={"category_id": "CUST_PAYMENT_REMINDER", "body": "Payment is due."},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["approval_status"] == "PENDING_HUMAN_CONFIRMATION"


@pytest.mark.asyncio
async def test_approve_pending_draft(auth_client):
    await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")

    thread_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER"},
    )
    thread_id = thread_resp.json()["id"]

    draft_resp = await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts",
        json={"category_id": "CUST_PAYMENT_REMINDER", "body": "Your balance is due."},
    )
    draft_id = draft_resp.json()["id"]
    assert draft_resp.json()["approval_status"] == "PENDING_HUMAN_CONFIRMATION"

    resp = await auth_client.post(f"/api/giraffe-jp/outbound-drafts/{draft_id}/approve")
    assert resp.status_code == 200, resp.text
    assert resp.json()["approval_status"] == "APPROVED"
    assert resp.json()["reviewed_by_user_id"] is not None


@pytest.mark.asyncio
async def test_reject_pending_draft(auth_client):
    await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")

    thread_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER"},
    )
    thread_id = thread_resp.json()["id"]

    draft_resp = await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts",
        json={"category_id": "CUST_ALTERATION_REQUEST", "body": "Alteration confirmed."},
    )
    draft_id = draft_resp.json()["id"]

    resp = await auth_client.post(f"/api/giraffe-jp/outbound-drafts/{draft_id}/reject")
    assert resp.status_code == 200, resp.text
    assert resp.json()["approval_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_approve_auto_sent_draft_returns_400(auth_client):
    """Cannot approve a draft that was already auto-sent."""
    await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")

    thread_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "CUSTOMER"},
    )
    thread_id = thread_resp.json()["id"]

    draft_resp = await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts",
        json={"category_id": "CUST_ORDER_CONFIRMATION", "body": "Your order is confirmed."},
    )
    assert draft_resp.json()["approval_status"] == "AUTO_SENT"
    draft_id = draft_resp.json()["id"]

    resp = await auth_client.post(f"/api/giraffe-jp/outbound-drafts/{draft_id}/approve")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_outbound_drafts(auth_client):
    thread_resp = await auth_client.post(
        "/api/giraffe-jp/conversations",
        json={"party_type": "SUPPLIER"},
    )
    thread_id = thread_resp.json()["id"]

    await auth_client.post(
        f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts",
        json={"category_id": "UNKNOWN_CAT", "body": "Message 1"},
    )
    resp = await auth_client.get(f"/api/giraffe-jp/conversations/{thread_id}/outbound-drafts")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) >= 1
