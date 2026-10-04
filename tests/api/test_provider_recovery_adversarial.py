"""Adversarial snapshots must preserve provider truth and commercial safety."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from src.db.models import Order, OrderLine
from src.order_confirmation.execution_persistence import snapshot_hash
from tests.api.test_provider_order_handoff import handoff, import_order


async def checkpoint(handoff):
    client, provider, sessions, *_ = handoff
    order = (await import_order(client)).json()
    response = await client.post(f"/api/orders/{order['id']}/request-qc")
    assert response.status_code == 200, response.text
    return client, provider, sessions, order


async def test_same_revision_reimport_recovers_stale_local_view(handoff):
    client, provider, sessions, order = await checkpoint(handoff)
    async with sessions() as db:
        local = await db.get(Order, uuid.UUID(order['id']))
        local.status = 'IN_PRODUCTION'
        await db.commit()
    revision = provider.revision
    recovered = await import_order(client)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()['status'] == 'QC_PENDING'
    assert provider.revision == revision


@pytest.mark.parametrize('status', ['READY_TO_SHIP', 'BUYER_SIGNED_OFF'])
async def test_hash_valid_snapshot_cannot_bypass_safety_evidence(handoff, status):
    client, provider, sessions, order = await checkpoint(handoff)
    lifecycle = provider.state['projection']['lifecycle']
    lifecycle['order']['status'] = status
    if status == 'BUYER_SIGNED_OFF':
        lifecycle['order']['buyer_signed_off_at'] = datetime.now(timezone.utc).isoformat()
    provider.state['projection']['lifecycle_hash'] = snapshot_hash(lifecycle)
    provider.revision += 1
    rejected = await import_order(client)
    assert rejected.status_code == 409, rejected.text
    async with sessions() as db:
        assert (await db.get(Order, uuid.UUID(order['id']))).status == 'QC_PENDING'


async def test_hash_valid_snapshot_cannot_rewrite_approved_order_price(handoff):
    client, provider, sessions, order = await checkpoint(handoff)
    lifecycle = provider.state['projection']['lifecycle']
    lifecycle['records']['order_lines'][0]['unit_price'] = 999.0
    provider.state['projection']['lifecycle_hash'] = snapshot_hash(lifecycle)
    provider.revision += 1
    rejected = await import_order(client)
    assert rejected.status_code == 409, rejected.text
    async with sessions() as db:
        line = await db.scalar(select(OrderLine).where(OrderLine.order_id == uuid.UUID(order['id'])))
        assert line.unit_price == 15.5


async def test_compact_requirements_restore_exact_confirmed_meaning(handoff):
    client, provider, sessions, order = await checkpoint(handoff)
    from tests.api.test_provider_lifecycle_recovery import fresh_execution_database
    attributes = provider.state['projection']['lifecycle']['records']['order_lines'][0]['attributes']
    assert 'form_fields_snapshot' not in attributes
    reference = attributes['confirmed_requirement_source']
    assert reference['source_snapshot_hash'] == provider.order['source_snapshot_hash']
    await fresh_execution_database(handoff[-1], sessions, handoff[3])
    restored = await import_order(client)
    assert restored.status_code == 200, restored.text
    async with sessions() as db:
        line = await db.scalar(select(OrderLine).where(OrderLine.order_id == uuid.UUID(order['id'])))
        assert line.attributes == {'form_fields_snapshot': provider.order['metadata_json']['confirmed_requirement_snapshot']['case']['requirement']}


async def test_compact_source_reference_must_match_confirmation(handoff):
    client, provider, sessions, order = await checkpoint(handoff)
    lifecycle = provider.state['projection']['lifecycle']
    lifecycle['records']['order_lines'][0]['attributes']['confirmed_requirement_source']['source_snapshot_hash'] = 'b' * 64
    provider.state['projection']['lifecycle_hash'] = snapshot_hash(lifecycle)
    provider.revision += 1
    assert (await import_order(client)).status_code == 409


@pytest.mark.parametrize('mutation', ['remove_resolution', 'foreign_actor', 'wrong_signoff_role', 'invalid_signoff_time', 'invalid_quantity_type'])
async def test_recovered_closure_retains_human_authorization(handoff, mutation):
    from tests.api.test_provider_lifecycle_recovery import advance
    client, provider, sessions, *_ = handoff
    order, _ = await advance(handoff)
    lifecycle = provider.state['projection']['lifecycle']
    events = lifecycle['records']['execution_events']
    if mutation == 'remove_resolution':
        lifecycle['records']['execution_events'] = [event for event in events if event['event_type'] != 'QC_FAILURE_RESOLVED']
    elif mutation == 'foreign_actor':
        signoff = next(event for event in events if event['event_type'] == 'BUYER_SIGNED_OFF')
        signoff['triggered_by_user_id'] = str(uuid.uuid4())
        signoff['payload']['actor_id'] = signoff['triggered_by_user_id']
    elif mutation == 'wrong_signoff_role':
        next(event for event in events if event['event_type'] == 'BUYER_SIGNED_OFF')['payload']['actor_role'] = 'supplier'
    elif mutation == 'invalid_signoff_time':
        next(event for event in events if event['event_type'] == 'BUYER_SIGNED_OFF')['payload']['signed_off_at'] = 'invalid'
    else:
        lifecycle['records']['order_lines'][0]['quantity'] = '10000'
    provider.state['projection']['lifecycle_hash'] = snapshot_hash(lifecycle)
    provider.revision += 1
    response = await import_order(client)
    assert response.status_code == 409, response.text


async def test_closure_replay_does_not_create_a_provider_revision(handoff):
    from tests.api.test_provider_lifecycle_recovery import advance
    client, provider, *_ = handoff
    order, _ = await advance(handoff)
    revision = provider.revision
    assert (await import_order(client)).status_code == 200
    response = await client.post(f"/api/orders/{order['id']}/buyer-sign-off")
    assert response.status_code == 200, response.text
    assert provider.revision == revision
