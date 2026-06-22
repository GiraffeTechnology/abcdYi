"""Integration tests for Giraffe JP formalwear C2B2M order extension API."""
import pytest
import uuid


@pytest.mark.asyncio
async def test_create_formalwear_profile_bridalwear(auth_client, seed_project):
    """BRIDALWEAR must set hollow_to_hem_required=True automatically."""
    resp = await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/formalwear-profile",
        json={"garment_category": "BRIDALWEAR", "hollow_to_hem_cm": 145.0},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["garment_category"] == "BRIDALWEAR"
    assert data["hollow_to_hem_required"] is True
    assert data["hollow_to_hem_cm"] == 145.0
    assert data["model_try_on_required"] is True
    assert data["local_alteration_possible"] is True


@pytest.mark.asyncio
async def test_create_formalwear_profile_womens_suit(auth_client, seed_project):
    """WOMENS_SUIT must set hollow_to_hem_required=False."""
    resp = await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/formalwear-profile",
        json={"garment_category": "WOMENS_SUIT"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["hollow_to_hem_required"] is False


@pytest.mark.asyncio
async def test_create_formalwear_profile_formal_dress(auth_client, seed_project):
    resp = await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/formalwear-profile",
        json={"garment_category": "FORMAL_DRESS", "hollow_to_hem_cm": 138.0},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["hollow_to_hem_required"] is True


@pytest.mark.asyncio
async def test_get_formalwear_profile(auth_client, seed_project):
    await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/formalwear-profile",
        json={"garment_category": "RECEPTION_DRESS"},
    )
    resp = await auth_client.get(
        f"/api/giraffe-jp/projects/{seed_project['id']}/formalwear-profile"
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["garment_category"] == "RECEPTION_DRESS"


@pytest.mark.asyncio
async def test_get_formalwear_profile_not_found(auth_client):
    resp = await auth_client.get(
        f"/api/giraffe-jp/projects/{uuid.uuid4()}/formalwear-profile"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_formalwear_profile(auth_client, seed_project):
    await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/formalwear-profile",
        json={"garment_category": "LIGHT_WEDDING_DRESS"},
    )
    resp = await auth_client.patch(
        f"/api/giraffe-jp/projects/{seed_project['id']}/formalwear-profile",
        json={"hollow_to_hem_cm": 152.0, "model_try_on_required": False},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["hollow_to_hem_cm"] == 152.0
    assert data["model_try_on_required"] is False


@pytest.mark.asyncio
async def test_initialize_c2b2m_edges(auth_client, seed_project):
    resp = await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/c2b2m-edges/initialize"
    )
    assert resp.status_code == 201, resp.text
    edges = resp.json()
    assert len(edges) == 4
    roles_from = {e["role_from"] for e in edges}
    assert "CUSTOMER" in roles_from
    assert "SERVICE_PLATFORM" in roles_from


@pytest.mark.asyncio
async def test_initialize_c2b2m_edges_idempotent(auth_client, seed_project):
    """Second call must not create duplicate edges."""
    resp1 = await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/c2b2m-edges/initialize"
    )
    resp2 = await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/c2b2m-edges/initialize"
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    # First call creates 4, second call creates 0 (idempotent)
    assert len(resp1.json()) == 4
    assert len(resp2.json()) == 0


@pytest.mark.asyncio
async def test_list_c2b2m_edges(auth_client, seed_project):
    await auth_client.post(
        f"/api/giraffe-jp/projects/{seed_project['id']}/c2b2m-edges/initialize"
    )
    resp = await auth_client.get(
        f"/api/giraffe-jp/projects/{seed_project['id']}/c2b2m-edges"
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 4


@pytest.mark.asyncio
async def test_formalwear_requires_auth(client, seed_project):
    resp = await client.get(
        f"/api/giraffe-jp/projects/{uuid.uuid4()}/formalwear-profile"
    )
    assert resp.status_code == 401
