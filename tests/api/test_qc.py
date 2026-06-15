import pytest


@pytest.mark.asyncio
async def test_create_qc_standard(auth_client, seed_confirmed_order):
    form_version_id = seed_confirmed_order.get("locked_form_version_id")
    if not form_version_id:
        pytest.skip("No locked form version")
    resp = await auth_client.post(
        f"/api/orders/{seed_confirmed_order['id']}/qc-standards",
        json={"form_version_id": form_version_id},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["order_id"] == seed_confirmed_order["id"]


@pytest.mark.asyncio
async def test_qc_pass(auth_client, seed_qc_order):
    resp = await auth_client.post(
        f"/api/orders/{seed_qc_order['id']}/qc-records",
        json={"label_compliance": True, "packaging_compliance": True},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["result"] == "QC_PASSED"


@pytest.mark.asyncio
async def test_qc_fail_creates_incident(auth_client, seed_qc_order, seed_participant, db):
    resp = await auth_client.post(
        f"/api/orders/{seed_qc_order['id']}/qc-records",
        json={
            "responsible_participant_id": seed_participant["id"],
            "fabric_defects": {"pin_holes": 5},
            "label_compliance": False,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["result"] == "QC_FAILED"

    from sqlalchemy import select
    from src.db.models.logistics import QualityIncident
    import uuid
    result = await db.execute(
        select(QualityIncident).where(
            QualityIncident.responsible_participant_id == uuid.UUID(seed_participant["id"])
        )
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_qc_pass_transitions_order(auth_client, seed_qc_order):
    resp = await auth_client.post(
        f"/api/orders/{seed_qc_order['id']}/qc-records",
        json={"label_compliance": True, "packaging_compliance": True},
    )
    assert resp.json()["result"] == "QC_PASSED"

    order_resp = await auth_client.get(f"/api/orders/{seed_qc_order['id']}")
    assert order_resp.json()["status"] == "READY_TO_SHIP"


@pytest.mark.asyncio
async def test_replacement_alert_at_3_incidents(auth_client, seed_qc_order, seed_participant, db):
    """Third quality incident should trigger replacement alert."""
    import uuid
    from sqlalchemy import select
    from src.db.models.logistics import QualityIncident, ReplacementAlert

    for _ in range(3):
        await auth_client.post(
            f"/api/orders/{seed_qc_order['id']}/qc-records",
            json={
                "responsible_participant_id": seed_participant["id"],
                "label_compliance": False,
            },
        )

    result = await db.execute(
        select(ReplacementAlert).where(
            ReplacementAlert.participant_id == uuid.UUID(seed_participant["id"])
        )
    )
    alert = result.scalar_one_or_none()
    assert alert is not None
    assert alert.quality_issue_count >= 3


@pytest.mark.asyncio
async def test_list_qc_records(auth_client, seed_qc_order):
    await auth_client.post(
        f"/api/orders/{seed_qc_order['id']}/qc-records",
        json={"label_compliance": True},
    )
    resp = await auth_client.get(f"/api/orders/{seed_qc_order['id']}/qc-records")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
