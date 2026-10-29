"""Immutable commercial quote/version binding using existing approval evidence."""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from fastapi import HTTPException
from sqlalchemy import select

from src.db.models.decision import ApprovalRequest, DecisionOption, DecisionPacket
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion, ClarificationQuestion
from src.db.models.project import Project
from src.db.models.user import User, UserRole

MATERIAL_FIELDS = {
    'product_type', 'quantity', 'fabric_type', 'fabric_composition', 'color',
    'size_range', 'size_breakdown', 'delivery_deadline', 'delivery_days',
    'qc_standard', 'quality_standard', 'trade_term', 'destination', 'unit_price',
    'fabric_material', 'size_ratio', 'packaging', 'packaging_requirement',
    'delivery_window', 'lead_time_days', 'quality_level', 'quality_criteria',
}


def unresolved_material_fields(*missing_collections):
    """Accept both form field names and Aivan's structured clarification flags.

    This identifies explicit unresolved material questions; it does not declare
    every optional apparel field mandatory or infer that a stated value has
    received human confirmation.
    """
    unresolved = set()
    for items in missing_collections:
        if items is None:
            continue
        if not isinstance(items, (list, tuple, set)):
            unresolved.add("invalid_requirement_status")
            continue
        for item in items:
            name = item.get("field_name", item.get("field")) if isinstance(item, dict) else item
            if not isinstance(name, str):
                unresolved.add("invalid_requirement_status")
            elif name in MATERIAL_FIELDS:
                unresolved.add(name)
    return unresolved


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str, allow_nan=False).encode()).hexdigest()


def option_digest(option):
    evidence = {k: v for k, v in (option.evidence or {}).items() if k != 'commercial_approval'}
    return digest({name: getattr(option, name) for name in (
        'id', 'packet_id', 'supplier_combination', 'unit_price', 'total_price', 'currency',
        'lead_time_breakdown', 'calculated_total_lead_time_days', 'supplier_stated_lead_time_days',
        'risk_flags', 'missing_fields',
    )} | {'evidence': evidence})


async def require_commercial_actor(db, user_id, tenant_id, *, buyer_only=False):
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail='Authorized human identity required')
    if user.is_platform_admin:
        return 'admin'
    allowed = {'buyer', 'buyer_proxy', 'admin'} if buyer_only else {'buyer', 'buyer_proxy', 'admin', 'approver', 'procurement', 'sales'}
    roles = await db.scalars(select(UserRole.role_name).where(UserRole.user_id == user_id))
    for role in roles:
        if role.lower() in allowed:
            return role
    raise HTTPException(status_code=403, detail='Authorized buyer role required' if buyer_only else 'Authorized commercial role required')


async def require_project(db, project_id, tenant_id):
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail='Project not found')
    from src.permissions.project_access import require_project_access
    await require_project_access(db, project_id)
    return project


async def form_for_project(db, form_version_id, project_id):
    version = await db.get(DynamicOrderFormVersion, form_version_id)
    form = await db.get(DynamicOrderForm, version.form_id) if version else None
    if form is None or form.project_id != project_id:
        raise HTTPException(status_code=409, detail='Quotation requirement version does not belong to project')
    return form, version


async def validate_material_requirements(db, version, option):
    """Block missing facts and open material clarifications, not optional fields."""
    fields = version.fields or {}
    if not isinstance(fields.get('product_type'), str) or not fields['product_type'].strip():
        raise HTTPException(status_code=409, detail='Product requirement is unresolved')
    quantity = fields.get('quantity')
    if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity <= 0:
        raise HTTPException(status_code=409, detail='Quantity requirement is unresolved')
    if unresolved_material_fields(version.missing_fields, fields.get('missing_fields')):
        raise HTTPException(status_code=409, detail='Material requirements remain unresolved')
    questions = await db.scalars(select(ClarificationQuestion).where(
        ClarificationQuestion.form_id == version.form_id, ClarificationQuestion.status == 'OPEN'))
    if any(question.field_reference in MATERIAL_FIELDS or question.field_reference is None for question in questions):
        raise HTTPException(status_code=409, detail='Material clarification remains open')
    if (not isinstance(option.unit_price, (int, float)) or not math.isfinite(option.unit_price)
            or option.unit_price <= 0 or not option.currency):
        raise HTTPException(status_code=409, detail='Commercial price remains unresolved')


async def validate_quote_binding(db, *, project_id, packet_id, option_id, approval_id, tenant_id):
    await require_project(db, project_id, tenant_id)
    packet = await db.scalar(select(DecisionPacket).where(DecisionPacket.id == packet_id).with_for_update())
    if packet is None or packet.project_id != project_id:
        raise HTTPException(status_code=404, detail='Decision packet not found for project')
    if packet.human_approval_status != 'APPROVED':
        raise HTTPException(status_code=403, detail='Decision packet is not approved')
    option = await db.get(DecisionOption, option_id)
    if option is None or option.packet_id != packet_id or packet.recommended_option_id != option_id:
        raise HTTPException(status_code=403, detail='The selected option is not the approved quotation')
    approval = await db.get(ApprovalRequest, approval_id)
    binding = (option.evidence or {}).get('commercial_approval') or {}
    if (approval is None or approval.tenant_id != tenant_id or approval.action_type != 'QUOTE_APPROVE'
            or approval.resource_type != 'decision_packet' or approval.resource_id != packet_id
            or approval.status != 'APPROVED' or approval.consumed_at is None
            or binding.get('approval_id') != str(approval_id) or not binding.get('actor_role')
            or binding.get('actor_id') != str(approval.reviewed_by)
            or not approval.reviewed_at or binding.get('approved_at') != approval.reviewed_at.isoformat()
            or binding.get('option_hash') != option_digest(option)
            or (approval.proposed_payload or {}).get('option_hashes', {}).get(str(option_id)) != binding.get('option_hash')
            or (approval.proposed_payload or {}).get('form_version_id') != binding.get('form_version_id')
            or (approval.proposed_payload or {}).get('requirement_hash') != binding.get('requirement_hash')):
        raise HTTPException(status_code=403, detail='Immutable quotation approval evidence does not match')
    try:
        version_id = uuid.UUID(binding['form_version_id'])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail='Approved requirement version missing') from exc
    form, version = await form_for_project(db, version_id, project_id)
    current = await db.scalar(select(DynamicOrderFormVersion).where(
        DynamicOrderFormVersion.form_id == form.id, DynamicOrderFormVersion.version_number == form.current_version))
    if binding.get('requirement_hash') != digest(version.fields) or current is None or digest(current.fields) != binding['requirement_hash']:
        raise HTTPException(status_code=409, detail='Requirements changed after approval; submit a revised quotation')
    await validate_material_requirements(db, version, option)
    return packet, option, form, version, binding
