"""Synthetic database/API regressions for AC-3 isolation and failed QC handling."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select, func

from api.deps import get_current_user
from api.main import app
from src.db.models import Tenant, User, Order, Milestone, ExecutionEvent
from src.db.models.user import UserRole
from src.db.models.qc import QCRecord
from src.db.models.participant import Participant
from src.db.models.production import ProductionUpdate
from tests.api.test_provider_order_handoff import handoff, import_order


async def started(handoff):
    client, _, sessions, user, _ = handoff
    response = await import_order(client)
    assert response.status_code == 200, response.text
    order = response.json()
    async with sessions() as db:
        milestone = await db.scalar(select(Milestone).where(Milestone.order_id == uuid.UUID(order['id'])))
        milestone_id = str(milestone.id)
    return client, sessions, user, order, milestone_id


async def other_user(sessions):
    tenant, uid = uuid.uuid4(), uuid.uuid4()
    async with sessions() as db:
        db.add(Tenant(id=tenant, name='Other synthetic tenant', slug=str(tenant)))
        await db.flush()
        db.add(User(id=uid, tenant_id=tenant, email=f'{uid}@example.invalid', hashed_password='not-a-credential'))
        await db.commit()
    return SimpleNamespace(id=uid, tenant_id=tenant)


async def inspection(client, order_id, passed):
    r = await client.post(f'/api/orders/{order_id}/request-qc')
    assert r.status_code == 200, r.text
    r = await client.post(f'/api/orders/{order_id}/qc-records', json={'label_compliance': passed})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize('action', ['milestone', 'monitor', 'update', 'delay', 'standard', 'record', 'list', 'mark-pass', 'mark-fail', 'resolve', 'shipment', 'tracking'])
async def test_execution_surfaces_hide_other_tenant(handoff, action):
    client, sessions, user, order, ms = await started(handoff)
    oid = order['id']
    qc = await inspection(client, oid, True)
    shipment = await client.post(f'/api/orders/{oid}/shipments', json={'carrier': 'Synthetic carrier'})
    assert shipment.status_code == 201
    foreign = await other_user(sessions)
    app.dependency_overrides[get_current_user] = lambda: foreign
    route, method, payload = {
        'milestone': (f'/api/milestones/{ms}', 'patch', {'notes': 'Unauthorized'}),
        'monitor': (f'/api/orders/{oid}/production-monitoring', 'get', None),
        'update': (f'/api/orders/{oid}/production-updates', 'post', {'update_text': 'Unauthorized'}),
        'delay': (f'/api/orders/{oid}/run-delay-prediction', 'post', None),
        'standard': (f'/api/orders/{oid}/qc-standards', 'post', {'form_version_id': order['locked_form_version_id']}),
        'record': (f'/api/orders/{oid}/qc-records', 'post', {'label_compliance': True}),
        'list': (f'/api/orders/{oid}/qc-records', 'get', None),
        'mark-pass': (f"/api/qc-records/{qc['id']}/mark-pass", 'post', None),
        'mark-fail': (f"/api/qc-records/{qc['id']}/mark-fail", 'post', {'responsible_participant_id': str(uuid.uuid4())}),
        'resolve': (f"/api/qc-records/{qc['id']}/resolve", 'post', {'reason': 'Unauthorized'}),
        'shipment': (f'/api/orders/{oid}/shipments', 'post', {'carrier': 'Unauthorized'}),
        'tracking': (f"/api/shipments/{shipment.json()['id']}/tracking-events", 'post', {
            'event_type': 'DELIVERED', 'occurred_at': datetime.now(timezone.utc).isoformat()}),
    }[action]
    response = await client.request(method, route, **({'json': payload} if payload else {}))
    assert response.status_code == 404, response.text
    app.dependency_overrides[get_current_user] = lambda: user
    response = await client.get(f'/api/orders/{oid}')
    assert response.json()['status'] == 'SHIPPED'


async def test_failed_qc_requires_authorized_recorded_rework_and_reinspection(handoff):
    client, sessions, user, order, _ = await started(handoff)
    oid = order['id']
    failed = await inspection(client, oid, False)
    assert (await client.post(f'/api/orders/{oid}/shipments', json={'carrier': 'Synthetic'})).status_code == 409
    assert (await client.post(f"/api/qc-records/{failed['id']}/mark-pass")).status_code == 409
    assert (await client.post(f'/api/orders/{oid}/qc-records', json={'label_compliance': True})).status_code == 409
    path = f"/api/qc-records/{failed['id']}/resolve"
    assert (await client.post(path, json={'reason': 'Inspect replacement labels'})).status_code == 403
    async with sessions() as db:
        db.add(UserRole(user_id=user.id, role_name='QUALITY_MANAGER'))
        await db.commit()
    resolved = await client.post(path, json={'reason': 'Inspect replacement labels'})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()['result'] == 'QC_FAILED'
    assert (await client.post(path, json={'reason': 'Replay'})).status_code == 409
    async with sessions() as db:
        event = await db.scalar(select(ExecutionEvent).where(ExecutionEvent.event_type == 'QC_FAILURE_RESOLVED'))
        assert event.payload['actor_id'] == str(user.id)
        assert event.payload['actor_role'] == 'QUALITY_MANAGER'
        assert event.payload['qc_record_id'] == failed['id']
        assert event.project_id == uuid.UUID(order['project_id'])
        assert event.occurred_at is not None
    await handoff[-1].dispose()
    assert (await client.get(f'/api/orders/{oid}')).json()['status'] == 'IN_PRODUCTION'
    passed = await inspection(client, oid, True)
    assert passed['id'] != failed['id']
    records = (await client.get(f'/api/orders/{oid}/qc-records')).json()
    assert [r['result'] for r in records] == ['QC_FAILED', 'QC_PASSED']
    assert (await client.get(f'/api/orders/{oid}')).json()['status'] == 'READY_TO_SHIP'


async def test_empty_qc_cannot_create_ready_to_ship(handoff):
    client, _, _, order, _ = await started(handoff)
    assert (await client.post(f"/api/orders/{order['id']}/request-qc")).status_code == 200
    response = await client.post(f"/api/orders/{order['id']}/qc-records", json={})
    assert response.status_code == 422
    assert (await client.get(f"/api/orders/{order['id']}")).json()['status'] == 'QC_PENDING'


async def test_qc_standard_is_bound_to_confirmed_version_and_idempotent(handoff):
    client, _, _, order, _ = await started(handoff)
    path = f"/api/orders/{order['id']}/qc-standards"
    assert (await client.post(path, json={'form_version_id': str(uuid.uuid4())})).status_code == 404
    one = await client.post(path, json={'form_version_id': order['locked_form_version_id']})
    two = await client.post(path, json={'form_version_id': order['locked_form_version_id']})
    assert one.status_code == two.status_code == 201
    assert one.json()['id'] == two.json()['id']


async def test_nested_references_reject_foreign_participants_and_wrong_order(handoff):
    client, sessions, _, order, ms = await started(handoff)
    foreign = await other_user(sessions)
    pid, other_order_id = uuid.uuid4(), uuid.uuid4()
    async with sessions() as db:
        db.add(Participant(id=pid, tenant_id=foreign.tenant_id, name='Foreign synthetic supplier'))
        db.add(Order(id=other_order_id, project_id=uuid.UUID(order['project_id']), status='IN_PRODUCTION'))
        await db.commit()
    assert (await client.patch(f'/api/milestones/{ms}', json={'responsible_participant_id': str(pid)})).status_code == 404
    assert (await client.post(f"/api/orders/{order['id']}/production-updates", json={
        'update_text': 'Synthetic evidence', 'submitted_by_participant_id': str(pid)})).status_code == 404
    assert (await client.post(f'/api/orders/{other_order_id}/production-updates', json={
        'update_text': 'Synthetic evidence', 'milestone_id': ms})).status_code == 404


async def test_milestone_change_keeps_previous_evidence_and_rejects_unknown_status(handoff):
    client, sessions, _, order, ms = await started(handoff)
    assert (await client.patch(f'/api/milestones/{ms}', json={'status': 'FAKE'})).status_code == 422
    first = await client.patch(f'/api/milestones/{ms}', json={'status': 'DELAYED', 'notes': 'Awaiting material'})
    assert first.status_code == 200, first.text
    second = await client.patch(f'/api/milestones/{ms}', json={'status': 'IN_PROGRESS', 'notes': 'Replacement material accepted'})
    assert second.status_code == 200
    async with sessions() as db:
        events = list(await db.scalars(select(ExecutionEvent).where(ExecutionEvent.event_type == 'MILESTONE_UPDATED').order_by(ExecutionEvent.occurred_at)))
        assert len(events) == 2
        assert events[1].payload['previous']['notes'] == 'Awaiting material'
        assert events[1].project_id == uuid.UUID(order['project_id'])
        assert await db.scalar(select(func.count()).select_from(ProductionUpdate)) == 2


async def test_carrier_delivery_only_requests_signoff(handoff):
    client, sessions, _, order, _ = await started(handoff)
    await inspection(client, order['id'], True)
    shipment = await client.post(f"/api/orders/{order['id']}/shipments", json={'carrier': 'Synthetic'})
    response = await client.post(f"/api/shipments/{shipment.json()['id']}/tracking-events", json={
        'event_type': 'DELIVERED', 'occurred_at': datetime.now(timezone.utc).isoformat()})
    assert response.status_code == 201
    recovered = (await client.get(f"/api/orders/{order['id']}")).json()
    assert recovered['status'] == 'DELIVERED'
    assert recovered['buyer_signed_off_at'] is None
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ExecutionEvent).where(ExecutionEvent.event_type == 'BUYER_SIGNOFF_REQUESTED')) == 1
        assert await db.scalar(select(func.count()).select_from(ExecutionEvent).where(ExecutionEvent.event_type == 'BUYER_SIGNED_OFF')) == 0


@pytest.mark.parametrize('suffix,method,body', [
    ('reference-images', 'get', None), ('reports', 'get', None), ('process-card', 'get', None),
    ('reference-images', 'post', {'image_path': 'synthetic.png', 'uploaded_by_actor_id': 'synthetic'}),
    ('process-card', 'post', {'category': 'apparel'}),
    ('compare', 'post', {'production_images': []}),
    ('buyer-decision', 'post', {'milestone_id': 'synthetic', 'buyer_actor_id': 'synthetic', 'decision': 'approve'}),
])
async def test_legacy_qc_routes_require_auth_and_project_tenant(handoff, suffix, method, body):
    client, sessions, user, order, _ = await started(handoff)
    path = f"/api/qc/{order['project_id']}/{suffix}"
    app.dependency_overrides.pop(get_current_user)
    response = await client.request(method, path, **({'json': body} if body else {}))
    assert response.status_code == 401
    foreign = await other_user(sessions)
    app.dependency_overrides[get_current_user] = lambda: foreign
    response = await client.request(method, path, **({'json': body} if body else {}))
    assert response.status_code == 404


async def test_transit_arrival_does_not_imply_final_delivery(handoff):
    client, _, _, order, _ = await started(handoff)
    await inspection(client, order['id'], True)
    shipment = await client.post(f"/api/orders/{order['id']}/shipments", json={'carrier': 'Synthetic'})
    response = await client.post(f"/api/shipments/{shipment.json()['id']}/tracking-events", json={
        'event_type': 'ARRIVAL', 'location': 'Transit warehouse', 'occurred_at': datetime.now(timezone.utc).isoformat()})
    assert response.status_code == 201
    assert (await client.get(f"/api/orders/{order['id']}")).json()['status'] == 'SHIPPED'


async def test_resolution_audit_failure_rolls_back_rework(handoff, monkeypatch):
    import httpx
    client, sessions, user, order, _ = await started(handoff)
    failed = await inspection(client, order['id'], False)
    async with sessions() as db:
        db.add(UserRole(user_id=user.id, role_name='QUALITY_MANAGER'))
        await db.commit()
    async def failed_event(*args, **kwargs):
        raise RuntimeError('Synthetic event persistence failure')
    monkeypatch.setattr('src.qc.service.emit_event', failed_event)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url='http://consumer.invalid') as failing:
        response = await failing.post(f"/api/qc-records/{failed['id']}/resolve", json={'reason': 'Synthetic rework'})
    assert response.status_code == 500
    assert (await client.get(f"/api/orders/{order['id']}")).json()['status'] == 'QC_FAILED'


@pytest.mark.parametrize('measurement', [{'size_deviation': {'chest': 10}}, {'color_difference': {'delta_e': 100}}, {'fabric_defects': {'pin_holes': 'unknown'}}])
async def test_missing_or_invalid_numeric_qc_criteria_never_auto_pass(handoff, measurement):
    client, sessions, _, order, _ = await started(handoff)
    oid = order['id']
    assert (await client.post(f'/api/orders/{oid}/request-qc')).status_code == 200
    response = await client.post(f'/api/orders/{oid}/qc-records', json=measurement)
    assert response.status_code == 422
    assert (await client.get(f'/api/orders/{oid}')).json()['status'] == 'QC_PENDING'
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(QCRecord)) == 0
