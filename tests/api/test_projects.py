import pytest


@pytest.mark.asyncio
async def test_create_project(auth_client):
    resp = await auth_client.post(
        "/api/projects",
        json={"title": "White Cotton Shirt Order"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "OPEN"


@pytest.mark.asyncio
async def test_import_buyer_inquiry(auth_client, seed_project):
    resp = await auth_client.post(
        f"/api/projects/{seed_project['id']}/buyer-inquiries",
        json={"raw_text": "We need 10,000 white cotton shirts, FOB Shenzhen, delivery in 45 days."},
    )
    assert resp.status_code == 201
    assert resp.json()["raw_text"] is not None


@pytest.mark.asyncio
async def test_project_timeline_has_events(auth_client, seed_project):
    resp = await auth_client.get(f"/api/projects/{seed_project['id']}/timeline")
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["event_type"] == "PROJECT_CREATED" for e in events)
