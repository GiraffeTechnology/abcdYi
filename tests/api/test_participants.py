import pytest


@pytest.mark.asyncio
async def test_create_participant(auth_client):
    resp = await auth_client.post(
        "/api/participants",
        json={
            "name": "Shanghai Textile Co.",
            "country": "CN",
            "contact_email": "info@example.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Shanghai Textile Co."
    assert data["profile_completeness_score"] >= 0.0


@pytest.mark.asyncio
async def test_assign_role(auth_client, seed_participant):
    resp = await auth_client.post(
        f"/api/participants/{seed_participant['id']}/roles",
        json={"role_name": "MANUFACTURER"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_assign_invalid_role(auth_client, seed_participant):
    resp = await auth_client.post(
        f"/api/participants/{seed_participant['id']}/roles",
        json={"role_name": "UNKNOWN_ROLE"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_participant_execution_event_emitted(auth_client, db):
    resp = await auth_client.post(
        "/api/participants",
        json={"name": "Test Co."},
    )
    assert resp.status_code == 201
    participant_id = resp.json()["id"]

    from src.db.models.execution_graph import ExecutionEvent
    from sqlalchemy import select

    result = await db.execute(
        select(ExecutionEvent).where(
            ExecutionEvent.participant_id == participant_id,
            ExecutionEvent.event_type == "PARTICIPANT_REGISTERED",
        )
    )
    event = result.scalar_one_or_none()
    assert event is not None
