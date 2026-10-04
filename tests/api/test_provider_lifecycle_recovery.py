"""Actual application/SQL lifecycle with synthetic HTTP contract responses.

These tests validate recovery and failure behavior, not live provider acceptance.
"""
import copy
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, func
from src.db.base import Base
from src.db.models import Tenant, User, UserRole, Order, Milestone, ExecutionEvent, SupplierMemoryRecord
from src.db.models.provider_order import ProviderOrderAssociation
from tests.api.test_provider_order_handoff import handoff, import_order
from src.order_confirmation.execution_persistence import snapshot_hash


async def roles(sessions, user):
    async with sessions() as db:
        db.add_all([UserRole(user_id=user.id, role_name=role) for role in ("BUYER", "QUALITY_MANAGER")])
        await db.commit()


async def advance(handoff):
    client, provider, sessions, user, _ = handoff
    await roles(sessions, user)
    result = await import_order(client)
    assert result.status_code == 200, result.text
    order = result.json(); oid = order['id']
    milestones = (await client.get(f'/api/orders/{oid}/production-monitoring')).json()['milestones']
    for milestone in milestones:
        if milestone['milestone_type'] in {'FABRIC_BOOKING', 'TRIM_BOOKING', 'CUTTING', 'SEWING', 'PACKING'}:
            response = await client.patch(f"/api/milestones/{milestone['id']}", json={
                'status': 'COMPLETED', 'actual_date': datetime.now(timezone.utc).isoformat(),
                'notes': 'Synthetic operator observed completed apparel work.'})
            assert response.status_code == 200, response.text
    r = await client.post(f'/api/orders/{oid}/request-qc'); assert r.status_code == 200, r.text
    failure = await client.post(f'/api/orders/{oid}/qc-records', json={'label_compliance': False})
    assert failure.status_code == 201, failure.text
    r = await client.post(f'/api/orders/{oid}/shipments', json={'carrier': 'Synthetic carrier'})
    assert r.status_code == 409
    r = await client.post(f"/api/qc-records/{failure.json()['id']}/resolve", json={'reason': 'Replace incorrect labels and reinspect the batch.'})
    assert r.status_code == 200, r.text
    r = await client.post(f'/api/orders/{oid}/request-qc'); assert r.status_code == 200, r.text
    r = await client.post(f'/api/orders/{oid}/qc-records', json={'label_compliance': True})
    assert r.status_code == 201, r.text
    shipment = await client.post(f'/api/orders/{oid}/shipments', json={'carrier': 'Synthetic carrier', 'tracking_number': 'SYNTHETIC-ONLY'})
    assert shipment.status_code == 201, shipment.text
    r = await client.post(f"/api/shipments/{shipment.json()['id']}/tracking-events", json={
        'event_type': 'DELIVERED', 'description': 'Carrier reported delivery; buyer review is still pending.',
        'occurred_at': datetime.now(timezone.utc).isoformat()})
    assert r.status_code == 201, r.text
    delivered = (await client.get(f'/api/orders/{oid}')).json()
    assert delivered['status'] == 'DELIVERED' and delivered['buyer_signed_off_at'] is None
    r = await client.post(f'/api/orders/{oid}/buyer-sign-off'); assert r.status_code == 200, r.text
    return order, r.json()


async def fresh_execution_database(engine, sessions, user):
    """Retain only the independently provisioned auth identity, no business state."""
    await engine.dispose()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        db.add(Tenant(id=user.tenant_id, name='Synthetic recovered tenant', slug=str(user.tenant_id)))
        await db.flush()
        db.add(User(id=user.id, tenant_id=user.tenant_id, email='synthetic@example.invalid', hashed_password='not-a-login-credential'))
        await db.commit()
    await roles(sessions, user)


async def test_complete_apparel_lifecycle_recovers_from_selected_provider(handoff):
    client, provider, sessions, user, engine = handoff
    original, completed = await advance(handoff)
    lifecycle = copy.deepcopy(provider.state['projection']['lifecycle'])
    revision = provider.revision
    assert lifecycle['order']['status'] == completed['status']
    assert lifecycle['order']['buyer_signed_off_at'] is not None
    assert len(lifecycle['records']['qc_records']) == 2
    assert len(lifecycle['records']['supplier_memory_records']) == 1
    assert any(row['event_type'] == 'QC_FAILURE_RESOLVED' for row in lifecycle['records']['execution_events'])
    await fresh_execution_database(engine, sessions, user)
    recovered = await import_order(client)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()['id'] == original['id']
    assert recovered.json()['status'] == completed['status']
    assert recovered.json()['buyer_signed_off_at'] == completed['buyer_signed_off_at']
    assert provider.revision == revision
    repeat = await client.post(f"/api/orders/{original['id']}/buyer-sign-off")
    assert repeat.status_code == 200
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(SupplierMemoryRecord)) == 1
        association = await db.get(ProviderOrderAssociation, uuid.UUID(original['id']))
        assert association.execution_revision == revision
        assert association.execution_snapshot_hash == snapshot_hash(lifecycle)
    graph = (await client.get(f"/api/execution-graph/orders/{original['id']}")).json()
    assert len(graph) == len(lifecycle['records']['execution_events'])


async def test_provider_failure_rolls_back_local_lifecycle(handoff):
    client, provider, sessions, *_ = handoff
    order = (await import_order(client)).json()
    provider.canonical_rejection = True
    rejected = await client.post(f"/api/orders/{order['id']}/request-qc")
    assert rejected.status_code == 422, rejected.text
    provider.canonical_rejection = False
    assert (await client.get(f"/api/orders/{order['id']}")).json()['status'] == 'IN_PRODUCTION'
    assert provider.revision == 1
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ExecutionEvent).where(ExecutionEvent.event_type == 'QC_REQUESTED')) == 0


async def test_lost_provider_reply_recovers_same_lifecycle_write(handoff):
    client, provider, *_ = handoff
    order = (await import_order(client)).json(); provider.lose_reply = True
    r = await client.post(f"/api/orders/{order['id']}/request-qc")
    assert r.status_code == 200, r.text
    assert provider.revision == 2
    r = await import_order(client)
    assert r.status_code == 200 and r.json()['status'] == 'QC_PENDING'
    assert provider.revision == 2


async def test_stale_executor_cannot_overwrite_provider_revision(handoff):
    client, provider, sessions, user, _ = handoff
    order = (await import_order(client)).json()
    assert (await client.post(f"/api/orders/{order['id']}/request-qc")).status_code == 200
    async with sessions() as db:
        association = await db.get(ProviderOrderAssociation, uuid.UUID(order['id']))
        association.execution_revision = 1; association.execution_snapshot_hash = None
        local = await db.get(Order, uuid.UUID(order['id'])); local.status = 'IN_PRODUCTION'
        await db.commit()
    r = await client.post(f"/api/orders/{order['id']}/request-qc")
    assert r.status_code == 409, r.text
    assert provider.revision == 2
    restored = await import_order(client)
    assert restored.status_code == 200 and restored.json()['status'] == 'QC_PENDING'


async def test_tampered_provider_snapshot_is_not_rehydrated(handoff):
    client, provider, sessions, user, engine = handoff
    order = (await import_order(client)).json()
    assert (await client.post(f"/api/orders/{order['id']}/request-qc")).status_code == 200
    provider.state['projection']['lifecycle']['order']['status'] = 'CLOSED'
    await fresh_execution_database(engine, sessions, user)
    rejected = await import_order(client)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()['detail']['error'] == 'PROVIDER_LIFECYCLE_HASH_MISMATCH'
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 0
