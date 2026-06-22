"""Integration tests for Giraffe JP service-core API (service nodes)."""
import pytest
import uuid


@pytest.mark.asyncio
async def test_create_service_node(auth_client):
    resp = await auth_client.post(
        "/api/giraffe-jp/service-nodes",
        json={"name": "Kyoto Atelier Co.", "node_type": "ATELIER", "location_country": "JP"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Kyoto Atelier Co."
    assert data["node_type"] == "ATELIER"
    assert data["location_country"] == "JP"
    assert "id" in data
    assert "tenant_id" in data


@pytest.mark.asyncio
async def test_list_service_nodes(auth_client):
    await auth_client.post(
        "/api/giraffe-jp/service-nodes",
        json={"name": "Osaka Fabric House", "node_type": "SUPPLIER"},
    )
    resp = await auth_client.get("/api/giraffe-jp/service-nodes")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_service_node(auth_client):
    create_resp = await auth_client.post(
        "/api/giraffe-jp/service-nodes",
        json={"name": "Tokyo Partner Studio", "node_type": "MODEL_PARTNER"},
    )
    node_id = create_resp.json()["id"]
    resp = await auth_client.get(f"/api/giraffe-jp/service-nodes/{node_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == node_id


@pytest.mark.asyncio
async def test_get_service_node_not_found(auth_client):
    resp = await auth_client.get(f"/api/giraffe-jp/service-nodes/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_service_nodes_require_auth(client):
    resp = await client.get("/api/giraffe-jp/service-nodes")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_service_node_with_metadata(auth_client):
    resp = await auth_client.post(
        "/api/giraffe-jp/service-nodes",
        json={
            "name": "Nara Embroidery Workshop",
            "node_type": "SPECIALIST",
            "location_country": "JP",
            "node_metadata": {"specialty": "Nishiki embroidery", "min_order": 5},
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["node_metadata"]["specialty"] == "Nishiki embroidery"
