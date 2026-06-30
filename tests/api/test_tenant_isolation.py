"""Cross-tenant isolation / IDOR tests (security P0 #2).

Every "fetch one resource by id" endpoint must scope to the caller's tenant.
A user authenticated in tenant B must never be able to read or mutate a
resource owned by tenant A; the server returns 404 (not 403) so resource
existence is not leaked across tenants.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.auth import hash_password
from src.db.base import AsyncSessionLocal


@pytest.fixture
async def other_tenant_client():
    """An authenticated client belonging to a *different* tenant."""
    from src.db.models.user import User
    from src.db.models.tenant import Tenant

    async with AsyncSessionLocal() as session:
        tenant = Tenant(name="Other Tenant", slug=f"other-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        email = f"other-{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=hash_password("otherpass"),
        )
        session.add(user)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/auth/login",
            data={"username": email, "password": "otherpass"},
        )
        assert resp.status_code == 200, resp.text
        ac.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
        yield ac


@pytest.mark.asyncio
async def test_cannot_read_other_tenant_project(
    auth_client, other_tenant_client, seed_project
):
    # Owner can read
    own = await auth_client.get(f"/api/projects/{seed_project['id']}")
    assert own.status_code == 200
    # Foreign tenant gets 404
    resp = await other_tenant_client.get(f"/api/projects/{seed_project['id']}")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_read_other_tenant_participant(
    auth_client, other_tenant_client, seed_participant
):
    resp = await other_tenant_client.get(f"/api/participants/{seed_participant['id']}")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_read_other_tenant_rfq(auth_client, other_tenant_client, seed_rfq):
    own = await auth_client.get(f"/api/rfqs/{seed_rfq['id']}")
    assert own.status_code == 200
    resp = await other_tenant_client.get(f"/api/rfqs/{seed_rfq['id']}")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_read_other_tenant_order(
    auth_client, other_tenant_client, seed_draft_order
):
    own = await auth_client.get(f"/api/orders/{seed_draft_order['id']}")
    assert own.status_code == 200
    resp = await other_tenant_client.get(f"/api/orders/{seed_draft_order['id']}")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_confirm_other_tenant_order(
    auth_client, other_tenant_client, seed_draft_order
):
    resp = await other_tenant_client.post(f"/api/orders/{seed_draft_order['id']}/confirm")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_read_other_tenant_approval_request(
    auth_client, other_tenant_client, seed_rfq
):
    approval_id = seed_rfq["approval_request_id"]
    own = await auth_client.get(f"/api/approval-requests/{approval_id}")
    assert own.status_code == 200
    resp = await other_tenant_client.get(f"/api/approval-requests/{approval_id}")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_cannot_approve_other_tenant_approval_request(
    auth_client, other_tenant_client, seed_rfq
):
    approval_id = seed_rfq["approval_request_id"]
    resp = await other_tenant_client.post(
        f"/api/approval-requests/{approval_id}/approve",
        json={"review_notes": "malicious"},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_other_tenant_approval_list_is_isolated(
    auth_client, other_tenant_client, seed_rfq
):
    """The foreign tenant must not see tenant A's approval requests in the list."""
    approval_id = seed_rfq["approval_request_id"]
    resp = await other_tenant_client.get("/api/approval-requests?status=ALL")
    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()}
    assert approval_id not in ids
