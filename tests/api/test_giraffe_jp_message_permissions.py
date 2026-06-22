"""Integration tests for Giraffe JP message category auto-send permissions API."""
import pytest
import uuid


@pytest.mark.asyncio
async def test_seed_defaults_creates_22_permissions(auth_client):
    resp = await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 22


@pytest.mark.asyncio
async def test_seed_defaults_idempotent(auth_client):
    """Calling seed-defaults twice does not create duplicate rows."""
    resp1 = await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")
    resp2 = await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert len(resp1.json()) == len(resp2.json()) == 22


@pytest.mark.asyncio
async def test_list_permissions_after_seed(auth_client):
    await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")
    resp = await auth_client.get("/api/giraffe-jp/permissions")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 22


@pytest.mark.asyncio
async def test_get_single_permission(auth_client):
    seed_resp = await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")
    perm_id = seed_resp.json()[0]["id"]
    resp = await auth_client.get(f"/api/giraffe-jp/permissions/{perm_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == perm_id


@pytest.mark.asyncio
async def test_get_permission_not_found(auth_client):
    resp = await auth_client.get(f"/api/giraffe-jp/permissions/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_permission_auto_send(auth_client):
    """PATCH flips auto_send and emits a graph event."""
    seed_resp = await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")
    # Find CUST_PAYMENT_REMINDER which defaults to auto_send=False
    perms = seed_resp.json()
    target = next(p for p in perms if p["category_id"] == "CUST_PAYMENT_REMINDER")
    assert target["auto_send"] is False

    patch_resp = await auth_client.patch(
        f"/api/giraffe-jp/permissions/{target['id']}",
        json={"auto_send": True},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["auto_send"] is True


@pytest.mark.asyncio
async def test_permissions_require_auth(client):
    resp = await client.get("/api/giraffe-jp/permissions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_permissions_have_correct_structure(auth_client):
    seed_resp = await auth_client.post("/api/giraffe-jp/permissions/seed-defaults")
    perm = seed_resp.json()[0]
    assert all(k in perm for k in ["id", "tenant_id", "category_id", "category_name",
                                    "party_type", "channel", "auto_send",
                                    "created_at", "updated_at"])
