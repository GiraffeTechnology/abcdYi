import pytest


@pytest.mark.asyncio
async def test_update_milestone(auth_client, seed_in_production_order):
    milestone_id = seed_in_production_order["milestones"][0]["id"]
    resp = await auth_client.patch(
        f"/api/milestones/{milestone_id}",
        json={"status": "IN_PROGRESS", "notes": "Cutting started"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_update_milestone_to_delayed_with_predicted_date(auth_client, seed_in_production_order):
    from datetime import datetime, timezone, timedelta
    milestone_id = seed_in_production_order["milestones"][0]["id"]
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    resp = await auth_client.patch(
        f"/api/milestones/{milestone_id}",
        json={"predicted_date": future},
    )
    assert resp.status_code == 200
    # Predicted date set past planned date → auto-DELAYED
    data = resp.json()
    assert data["predicted_date"] is not None


@pytest.mark.asyncio
async def test_run_delay_prediction(auth_client, seed_in_production_order):
    resp = await auth_client.post(
        f"/api/orders/{seed_in_production_order['id']}/run-delay-prediction"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "delay_risk_level" in data
    assert "expedite_alert_required" in data


@pytest.mark.asyncio
async def test_delay_prediction_creates_alert_for_high_risk(auth_client, seed_delayed_order):
    resp = await auth_client.post(
        f"/api/orders/{seed_delayed_order['id']}/run-delay-prediction"
    )
    assert resp.status_code == 200
    packet = resp.json()
    if packet["delay_risk_level"] in ("HIGH", "CRITICAL"):
        assert packet["expedite_alert_required"] is True
        approvals = await auth_client.get("/api/approval-requests?status=PENDING")
        expedite = [a for a in approvals.json() if a["action_type"] == "EXPEDITE_NOTIFY"]
        assert len(expedite) >= 1


@pytest.mark.asyncio
async def test_expedite_alert_not_sent_without_approval(auth_client, seed_expedite_alert):
    assert "monitoring_packet" in seed_expedite_alert
    resp = await auth_client.post(
        f"/api/orders/{seed_expedite_alert['order_id']}/run-delay-prediction"
    )
    assert resp.status_code == 200
    assert "expedite_alert_required" in resp.json()


@pytest.mark.asyncio
async def test_production_monitoring_view(auth_client, seed_in_production_order):
    resp = await auth_client.get(
        f"/api/orders/{seed_in_production_order['id']}/production-monitoring"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "milestones" in data
    assert len(data["milestones"]) == 12


@pytest.mark.asyncio
async def test_add_production_update(auth_client, seed_in_production_order):
    resp = await auth_client.post(
        f"/api/orders/{seed_in_production_order['id']}/production-updates",
        json={"update_text": "Fabric arrived on time."},
    )
    assert resp.status_code == 201
    assert resp.json()["update_text"] == "Fabric arrived on time."
