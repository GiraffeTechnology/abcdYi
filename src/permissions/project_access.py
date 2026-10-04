"""Explicit project membership and narrowly scoped execution capabilities."""
from __future__ import annotations
import re
import uuid
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from api.deps import get_current_user, get_db
from src.db.models.project import Project
from src.db.models.project_membership import ProjectMembership
from src.db.models.user import User

INTERNAL_ROLES = {'BUYER', 'BUYER_PROXY', 'PROCUREMENT', 'PROJECT_OPERATOR'}
EXTERNAL_ROLES = {'MANUFACTURER', 'QC_INSPECTOR', 'LOGISTICS_PROVIDER'}


async def bind_request_actor(request: Request, current_user=Depends(get_current_user), db=Depends(get_db)):
    db.info['request_actor_id'] = current_user.id
    db.info['request_path'] = request.url.path
    db.info['request_method'] = request.method
    # Resolve URL resource IDs before a route can use an unscoped db.get.
    route_projects = set()
    for name, value in request.path_params.items():
        project_id, tenant_id = await resource_scope(db, name, value)
        if tenant_id is not None and tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail='Resource not found')
        if project_id is not None:
            await require_project_access(db, project_id)
            route_projects.add(project_id)
    # Use the selected provider as business truth before reading or changing
    # an imported order, including after an interrupted prior local commit.
    from src.db.models import Order, Milestone, QCRecord, Shipment
    from src.order_confirmation.execution_persistence import refresh_execution
    order_ids = set()
    if 'order_id' in request.path_params:
        order_ids.add(uuid.UUID(str(request.path_params['order_id'])))
    for key, model in {'milestone_id': Milestone, 'qc_record_id': QCRecord, 'shipment_id': Shipment}.items():
        if key in request.path_params:
            row = await db.get(model, uuid.UUID(str(request.path_params[key])))
            if row is not None:
                order_ids.add(row.order_id)
    for order_id in order_ids:
        await refresh_execution(db, tenant_id=current_user.tenant_id, order_id=order_id)
    if request.method in {'POST', 'PATCH', 'PUT'}:
        try:
            body = await request.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            for name in {'form_version_id', 'packet_id', 'option_id', 'approval_id', 'inquiry_id', 'rfq_id', 'milestone_id', 'responsible_participant_id', 'inspector_participant_id', 'submitted_by_participant_id', 'buyer_participant_id', 'logistics_provider_participant_id'}:
                value = body.get(name)
                if value is None:
                    continue
                scope_name = 'participant_id' if name.endswith('_participant_id') else name
                project_id, tenant_id = await resource_scope(db, scope_name, value)
                if tenant_id is not None and tenant_id != current_user.tenant_id:
                    raise HTTPException(status_code=404, detail='Resource not found')
                if project_id is not None:
                    await require_project_access(db, project_id)
                    if route_projects and project_id not in route_projects:
                        raise HTTPException(status_code=404, detail='Resource not found')


def _external_surface(role, path, method):
    # No quote, competing response, project audit, participant directory or raw
    # evidence listing is exposed by a production/logistics-only membership.
    if method == 'GET':
        return bool(re.fullmatch(r'/api/orders/[^/]+(?:/production-monitoring|/qc-records)?', path)
                    or role == 'LOGISTICS_PROVIDER' and re.fullmatch(r'/api/shipments/[^/]+', path))
    if role == 'MANUFACTURER':
        return bool(re.fullmatch(r'/api/milestones/[^/]+|/api/orders/[^/]+/(?:production-updates|request-qc)', path))
    if role == 'QC_INSPECTOR':
        return bool(re.fullmatch(r'/api/orders/[^/]+/qc-records', path))
    return bool(re.fullmatch(r'/api/orders/[^/]+/shipments|/api/shipments/[^/]+/tracking-events', path))


async def project_access_permitted(db, project_id):
    actor_id = db.info.get('request_actor_id')
    if actor_id is None:
        # Internal services/tests supply their own actor/tenant authorization;
        # all authenticated HTTP project surfaces install bind_request_actor.
        return True
    project = await db.get(Project, project_id)
    user = await db.get(User, actor_id)
    if project is None or user is None or not user.is_active or user.tenant_id != project.tenant_id:
        return False
    if project.created_by == actor_id or user.is_platform_admin:
        return True
    grant = await db.scalar(select(ProjectMembership).where(
        ProjectMembership.project_id == project_id, ProjectMembership.user_id == actor_id,
        ProjectMembership.revoked_at.is_(None)))
    if grant is None:
        return False
    if grant.role in INTERNAL_ROLES:
        return True
    return grant.role in EXTERNAL_ROLES and _external_surface(grant.role, db.info.get('request_path', ''), db.info.get('request_method', ''))


async def require_project_access(db, project_id):
    if not await project_access_permitted(db, project_id):
        raise HTTPException(status_code=404, detail='Project not found')


async def resource_scope(db, name, value):
    """Resolve known relational URL identities, never trust caller role hints."""
    from src.db.models import (DynamicOrderForm, DynamicOrderFormVersion, DecisionPacket,
        DecisionOption, ApprovalRequest, RFQ, SupplierResponse, Order, Milestone,
        QCRecord, Shipment, ExecutionEvent, Participant, BuyerInquiry)
    models = {'project_id': Project, 'form_id': DynamicOrderForm, 'form_version_id': DynamicOrderFormVersion,
              'packet_id': DecisionPacket, 'option_id': DecisionOption, 'approval_id': ApprovalRequest,
              'rfq_id': RFQ, 'response_id': SupplierResponse, 'order_id': Order,
              'milestone_id': Milestone, 'qc_record_id': QCRecord, 'shipment_id': Shipment,
              'event_id': ExecutionEvent, 'participant_id': Participant, 'inquiry_id': BuyerInquiry}
    if name not in models:
        return None, None
    try:
        identifier = uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=404, detail='Resource not found')
    row = await db.get(models[name], identifier)
    if row is None:
        raise HTTPException(status_code=404, detail='Resource not found')
    tenant = getattr(row, 'tenant_id', None)
    if name == 'project_id': return row.id, row.tenant_id
    if name == 'form_version_id': return await resource_scope(db, 'form_id', row.form_id)
    if name == 'option_id': return await resource_scope(db, 'packet_id', row.packet_id)
    if name == 'response_id': return await resource_scope(db, 'rfq_id', row.rfq_id)
    if name == 'approval_id':
        types = {'rfq':'rfq_id', 'decision_packet':'packet_id', 'order':'order_id'}
        if row.resource_type in types and row.resource_id:
            project, _tenant = await resource_scope(db, types[row.resource_type], row.resource_id)
            return project, tenant
    project_id = getattr(row, 'project_id', None)
    if project_id is None and getattr(row, 'order_id', None):
        return await resource_scope(db, 'order_id', row.order_id)
    if project_id is not None:
        project = await db.get(Project, project_id)
        if project is None: raise HTTPException(status_code=404, detail='Resource not found')
        return project_id, project.tenant_id
    return None, tenant
