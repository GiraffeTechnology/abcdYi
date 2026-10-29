"""Provider recovery of GLTG reforecast evidence; synthetic dependency response."""
import copy
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from src.db.models import DeliveryFeasibilityPacketRecord, ExecutionEvent
from src.lead_time.gltg_models import DeliveryFeasibilityPacket, DeliveryPath
from src.order_confirmation.execution_persistence import snapshot_hash
from tests.api.test_provider_order_handoff import handoff, import_order
from tests.api.test_provider_lifecycle_recovery import fresh_execution_database


@pytest.mark.parametrize("tamper", [None, "tenant", "date"])
async def test_reforecast_analysis_survives_fresh_execution_database(handoff, monkeypatch, tamper):
    client, provider, sessions, user, engine = handoff
    order = (await import_order(client)).json()
    day = date(2027, 1, 15)
    path = DeliveryPath('synthetic-path', ['synthetic-factory'], 2, 3, 5,
        day, day, day, day, ['cutting', 'sewing'], 5, True,
        'Synthetic feasible option', ['synthetic-risk'], ['synthetic-source'], 12.5, 'USD')
    packet = DeliveryFeasibilityPacket(order_id=order['id'], earliest_delivery_date=day,
        most_likely_delivery_date=day, risk_adjusted_delivery_date=day,
        committable_delivery_date=day, required_delivery_date=day,
        delivery_feasibility='FEASIBLE', days_vs_deadline=0,
        critical_path=['cutting', 'sewing'], critical_path_days=5,
        ranked_options=[path], option_count=1, risk_flags=['synthetic-risk'],
        missing_evidence=['synthetic-source'], explanation='Synthetic GLTG analysis', confidence='HIGH')
    monkeypatch.setattr('src.services.delivery_feasibility_service.evaluate_delivery_feasibility', lambda _: packet)
    response = await client.post(f"/api/orders/{order['id']}/run-delay-prediction")
    assert response.status_code == 200, response.text
    records = provider.state['projection']['lifecycle']['records']
    rows = copy.deepcopy(records['delivery_feasibility_packets'])
    assert len(rows) == 1
    assert rows[0]['ranked_options_json'][0]['path_id'] == 'synthetic-path'
    assert rows[0]['raw_gltg_packet_json']['explanation'] == packet.explanation
    assert rows[0]['required_delivery_date'] == day.isoformat()
    if tamper:
        row = records['delivery_feasibility_packets'][0]
        row['tenant_id' if tamper == 'tenant' else 'required_delivery_date'] = (
            str(uuid.uuid4()) if tamper == 'tenant' else '2027-99-99')
        provider.state['projection']['lifecycle_hash'] = snapshot_hash(provider.state['projection']['lifecycle'])
    revision = provider.revision
    await fresh_execution_database(engine, sessions, user)
    recovered = await import_order(client)
    if tamper:
        assert recovered.status_code == 409, recovered.text
        assert recovered.json()['detail']['error'] == (
            'PROVIDER_LIFECYCLE_SCOPE_MISMATCH' if tamper == 'tenant' else 'PROVIDER_LIFECYCLE_RECORD_INVALID')
        async with sessions() as db:
            assert await db.get(DeliveryFeasibilityPacketRecord, uuid.UUID(rows[0]['id'])) is None
        return
    assert recovered.status_code == 200, recovered.text
    async with sessions() as db:
        record = await db.get(DeliveryFeasibilityPacketRecord, uuid.UUID(rows[0]['id']))
        assert record is not None
        assert record.order_id == uuid.UUID(order['id'])
        assert record.required_delivery_date == day
        assert record.ranked_options_json == rows[0]['ranked_options_json']
        assert record.raw_gltg_packet_json == rows[0]['raw_gltg_packet_json']
        assert record.explanation == rows[0]['explanation']
        events = (await db.scalars(select(ExecutionEvent).where(ExecutionEvent.event_type == 'DELIVERY_FEASIBILITY_EVALUATED'))).all()
        assert any(event.payload['feasibility_packet_id'] == str(record.id) for event in events)
    assert provider.revision == revision


async def test_legacy_snapshot_without_reforecast_collection_remains_readable(handoff):
    client, provider, sessions, user, engine = handoff
    order = (await import_order(client)).json()
    response = await client.post(f"/api/orders/{order['id']}/request-qc")
    assert response.status_code == 200, response.text
    lifecycle = provider.state['projection']['lifecycle']
    lifecycle['records'].pop('delivery_feasibility_packets', None)
    provider.state['projection']['lifecycle_hash'] = snapshot_hash(lifecycle)
    await fresh_execution_database(engine, sessions, user)
    restored = await import_order(client)
    assert restored.status_code == 200, restored.text
    assert restored.json()['status'] == 'QC_PENDING'
