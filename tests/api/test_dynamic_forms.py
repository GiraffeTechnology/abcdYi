import pytest


@pytest.mark.asyncio
async def test_create_dynamic_form_from_inquiry(auth_client, seed_inquiry):
    resp = await auth_client.post(
        f"/api/projects/{seed_inquiry['project_id']}/dynamic-forms",
        json={"inquiry_id": seed_inquiry["id"]},
    )
    assert resp.status_code == 201
    form = resp.json()
    assert form["version_number"] == 1
    assert "fields" in form
    assert "missing_fields" in form


@pytest.mark.asyncio
async def test_update_form_creates_new_version(auth_client, seed_form):
    resp = await auth_client.patch(
        f"/api/dynamic-forms/{seed_form['form_id']}",
        json={
            "field_updates": {"quantity": 10000, "color": "White"},
            "confirmed_fields": ["quantity", "color"],
        },
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["version_number"] == 2
    assert "quantity" in updated["human_confirmed_fields"]


@pytest.mark.asyncio
async def test_locked_form_cannot_be_updated(auth_client, seed_locked_form):
    resp = await auth_client.patch(
        f"/api/dynamic-forms/{seed_locked_form['form_id']}",
        json={"field_updates": {"quantity": 999}, "confirmed_fields": []},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_dynamic_form_emits_execution_event(auth_client, seed_inquiry, db):
    await auth_client.post(
        f"/api/projects/{seed_inquiry['project_id']}/dynamic-forms",
        json={"inquiry_id": seed_inquiry["id"]},
    )
    from sqlalchemy import select
    from src.db.models.execution_graph import ExecutionEvent

    result = await db.execute(
        select(ExecutionEvent).where(
            ExecutionEvent.project_id == seed_inquiry["project_id"],
            ExecutionEvent.event_type == "DYNAMIC_FORM_CREATED",
        )
    )
    assert result.scalar_one_or_none() is not None
