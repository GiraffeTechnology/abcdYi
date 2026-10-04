"""Synthetic regression evidence for approved quotation/order/closure boundaries."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, func

from api.main import app
from src.db.models import Order, Project, ExecutionEvent
from src.db.models.user import UserRole
from src.db.models.decision import DecisionPacket, DecisionOption, ApprovalRequest
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion, ClarificationQuestion
from src.db.models.logistics import SupplierMemoryRecord
from src.db.models.rfq import RFQ, RFQRecipient
from src.order_confirmation.approval_binding import digest, option_digest
from tests.api.test_provider_order_handoff import handoff, import_order


async def quote(handoff, missing=None):
    client, _, sessions, user, _ = handoff
    async with sessions() as db:
        db.add(UserRole(user_id=user.id, role_name='BUYER'))
        project = Project(tenant_id=user.tenant_id, created_by=user.id, title='Synthetic approval binding')
        db.add(project)
        await db.flush()
        form = DynamicOrderForm(project_id=project.id)
        db.add(form)
        await db.flush()
        fields = {'product_type': 'Cotton shirt', 'quantity': 100, 'fabric_type': 'Cotton', 'size_range': 'M',
                  'color': 'White', 'delivery_deadline': '2027-01-15', 'trade_term': 'FOB', 'destination': 'Shenzhen',
                  'missing_fields': missing or []}
        version = DynamicOrderFormVersion(form_id=form.id, version_number=1, fields=fields, missing_fields=missing or [])
        packet = DecisionPacket(project_id=project.id, human_approval_status='PENDING')
        db.add_all([version, packet])
        await db.flush()
        option = DecisionOption(packet_id=packet.id, option_index=1, unit_price=10.0, currency='USD', evidence={'synthetic': True})
        db.add(option)
        await db.flush()
        approval = ApprovalRequest(tenant_id=user.tenant_id, action_type='QUOTE_APPROVE', resource_type='decision_packet',
            resource_id=packet.id, proposed_payload={'packet_id': str(packet.id), 'project_id': str(project.id),
                'form_version_id': str(version.id), 'requirement_hash': digest(fields), 'option_hashes': {str(option.id): option_digest(option)}})
        db.add(approval)
        await db.commit()
        return {'project_id': str(project.id), 'packet_id': str(packet.id), 'option_id': str(option.id),
                'approval_id': str(approval.id), 'form_id': str(form.id), 'version_id': str(version.id)}


async def approve(client, q):
    response = await client.post(f"/api/approval-requests/{q['approval_id']}/approve", json={'review_notes': 'Synthetic human review'})
    assert response.status_code == 200, response.text
    response = await client.post(f"/api/decision-packets/{q['packet_id']}/approve-option", json={
        'option_id': q['option_id'], 'approval_id': q['approval_id']})
    assert response.status_code == 200, response.text


async def create(client, q, **changes):
    body = {key: q[key] for key in ('packet_id', 'option_id', 'approval_id')}
    body.update(changes)
    return await client.post(f"/api/projects/{q['project_id']}/orders/from-approved-option", json=body)


async def test_approval_option_cannot_come_from_another_packet(handoff):
    client = handoff[0]
    first, second = await quote(handoff), await quote(handoff)
    assert (await client.post(f"/api/approval-requests/{first['approval_id']}/approve", json={})).status_code == 200
    response = await client.post(f"/api/decision-packets/{first['packet_id']}/approve-option", json={
        'option_id': second['option_id'], 'approval_id': first['approval_id']})
    assert response.status_code == 404
    own = await client.post(f"/api/decision-packets/{first['packet_id']}/approve-option", json={
        'option_id': first['option_id'], 'approval_id': first['approval_id']})
    assert own.status_code == 200, own.text


@pytest.mark.parametrize('changed', ['price', 'requirement', 'new_version'])
async def test_material_changes_after_approval_cannot_create_order(handoff, changed):
    client, _, sessions, _, _ = handoff
    q = await quote(handoff)
    await approve(client, q)
    async with sessions() as db:
        if changed == 'price':
            (await db.get(DecisionOption, uuid.UUID(q['option_id']))).unit_price = 20.0
        else:
            version = await db.get(DynamicOrderFormVersion, uuid.UUID(q['version_id']))
            if changed == 'requirement':
                version.fields = {**version.fields, 'quantity': 200}
            else:
                db.add(DynamicOrderFormVersion(form_id=version.form_id, version_number=2,
                    fields={**version.fields, 'quantity': 200}, missing_fields=[]))
                (await db.get(DynamicOrderForm, version.form_id)).current_version = 2
        await db.commit()
    response = await create(client, q)
    assert response.status_code in (403, 409), response.text
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 0


async def test_order_requires_exact_approval_option_and_project(handoff):
    client, _, sessions, _, _ = handoff
    q, other = await quote(handoff), await quote(handoff)
    await approve(client, q)
    for changes in ({'approval_id': other['approval_id']}, {'option_id': other['option_id']}):
        assert (await create(client, q, **changes)).status_code == 404
    swapped = {**q, 'project_id': other['project_id']}
    assert (await create(client, swapped)).status_code == 404
    response = await create(client, q)
    assert response.status_code == 201, response.text
    duplicate = await create(client, q)
    assert duplicate.json()['id'] == response.json()['id']
    assert (await client.post(f"/api/approval-requests/{q['approval_id']}/approve", json={})).status_code == 409
    assert (await client.post(f"/api/approval-requests/{q['approval_id']}/reject", json={})).status_code == 409
    confirm = await client.post(f"/api/orders/{response.json()['id']}/confirm")
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()['status'] == 'IN_PRODUCTION'
    again = await client.post(f"/api/orders/{response.json()['id']}/confirm")
    assert again.status_code == 200
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 1
        events = list(await db.scalars(select(ExecutionEvent).where(ExecutionEvent.event_type == 'ORDER_CONFIRMED')))
        assert len(events) == 1
        assert events[0].payload['actor_role'] in {'BUYER', 'PROCUREMENT'}
        assert events[0].payload['approval']['form_version_id'] == q['version_id']


@pytest.mark.parametrize('missing,expected', [(['qc_standard'], 409), (['quantity'], 409), (['special_notes'], 201),
    ([{'field_name': 'fabric_material'}], 409), ([{'field_name': 'size_ratio'}], 409),
    ([{'field_name': 'packaging'}], 409), ([{'field_name': 'special_notes'}], 201)])
async def test_material_gaps_block_orders_but_optional_fields_do_not(handoff, missing, expected):
    q = await quote(handoff, missing=missing)
    client = handoff[0]
    await approve(client, q)
    response = await create(client, q)
    assert response.status_code == expected, response.text


async def test_unresolved_material_clarification_blocks_order(handoff):
    q = await quote(handoff)
    client, _, sessions, _, _ = handoff
    await approve(client, q)
    async with sessions() as db:
        db.add(ClarificationQuestion(form_id=uuid.UUID(q['form_id']), question_text='Confirm quality tolerance', field_reference='qc_standard'))
        await db.commit()
    assert (await create(client, q)).status_code == 409


async def test_signoff_role_observed_supplier_evidence_and_retry(handoff):
    client, _, sessions, user, engine = handoff
    response = await import_order(client)
    assert response.status_code == 200
    order = response.json()
    oid = order['id']
    async with sessions() as db:
        option = await db.get(DecisionOption, uuid.UUID(order['approved_option_id']))
        supplier_id = uuid.UUID(option.supplier_combination['manufacturer'])
        foreign_project = Project(tenant_id=user.tenant_id, title='Other synthetic project')
        db.add(foreign_project)
        await db.flush()
        now = datetime.now(timezone.utc)
        for project_id, hours, offset in ((uuid.UUID(order['project_id']), 2, 0), (foreign_project.id, 99, 1)):
            rfq = RFQ(project_id=project_id, form_version_id=uuid.UUID(order['locked_form_version_id']))
            db.add(rfq)
            await db.flush()
            db.add(RFQRecipient(rfq_id=rfq.id, participant_id=supplier_id,
                sent_at=now-timedelta(hours=hours)+timedelta(days=offset), responded_at=now+timedelta(days=offset)))
        await db.commit()
    assert (await client.post(f'/api/orders/{oid}/request-qc')).status_code == 200
    qc = await client.post(f'/api/orders/{oid}/qc-records', json={'label_compliance': True, 'responsible_participant_id': str(supplier_id)})
    assert qc.status_code == 201
    shipment = await client.post(f'/api/orders/{oid}/shipments', json={'carrier': 'Synthetic'})
    assert shipment.status_code == 201
    response = await client.post(f"/api/shipments/{shipment.json()['id']}/tracking-events", json={
        'event_type': 'DELIVERED', 'occurred_at': datetime.now(timezone.utc).isoformat()})
    assert response.status_code == 201
    assert (await client.post(f'/api/orders/{oid}/buyer-sign-off')).status_code == 403
    async with sessions() as db:
        db.add(UserRole(user_id=user.id, role_name='BUYER'))
        await db.commit()
    response = await client.post(f'/api/orders/{oid}/buyer-sign-off')
    assert response.status_code == 200, response.text
    await engine.dispose()
    repeated = await client.post(f'/api/orders/{oid}/buyer-sign-off')
    assert repeated.status_code == 200
    async with sessions() as db:
        records = list(await db.scalars(select(SupplierMemoryRecord).where(SupplierMemoryRecord.order_id == uuid.UUID(oid))))
        assert len(records) == 1
        assert records[0].response_time_hours == 2
        assert records[0].qc_pass_rate == 1
        assert records[0].on_time_delivery is None  # Forecasts are not completed facts.
        events = list(await db.scalars(select(ExecutionEvent).where(ExecutionEvent.event_type == 'SUPPLIER_PERFORMANCE_RECORDED')))
        assert len(events) == 1
        assert events[0].payload['source_qc_record_ids'] == [qc.json()['id']]
        closure = list(await db.scalars(select(ExecutionEvent).where(ExecutionEvent.event_type == 'BUYER_SIGNED_OFF')))
        assert len(closure) == 1
        assert closure[0].payload['actor_role'] == 'BUYER'
