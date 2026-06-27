"""Adapter between abcdYi order data and the standalone GLTG API.

Builds GLTG API requests from abcdYi's database models and maps GLTG responses
into abcdYi's feasibility DTOs. No lead-time / path / feasibility calculation
happens here -- that is owned by the standalone GLTG service. On GLTG failure
this raises ``GLTGUnavailableError`` rather than falling back to a local engine.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.lead_time.gltg_models import (
    ApparelOrderInput,
    DeliveryFeasibilityPacket,
    DeliveryPath,
    ParticipantNode,
)
from src.integrations.gltg_client import GLTGClient

from src.db.models.order import Order
from src.db.models.dynamic_form import DynamicOrderFormVersion
from src.db.models.rfq import RFQ, SupplierResponse, SupplierResponsePacket
from src.db.models.participant import Participant, ParticipantRole, ParticipantProfile
from src.db.models.production import Milestone


class GLTGUnavailableError(RuntimeError):
    """Raised when the standalone GLTG service cannot be reached or errors."""

# GLTG role names mapped from abcdYi participant role_name values
_ROLE_MAP: dict[str, str] = {
    "MANUFACTURER": "MANUFACTURER",
    "FABRIC_SUPPLIER": "FABRIC_SUPPLIER",
    "TRIM_SUPPLIER": "TRIM_SUPPLIER",
    "PACKAGING_SUPPLIER": "PACKAGING_SUPPLIER",
    "QC_INSPECTOR": "QC_INSPECTOR",
    "LOGISTICS_PROVIDER": "LOGISTICS_PROVIDER",
}


async def _load_response_packet(
    db: AsyncSession, participant_id: uuid.UUID, rfq_id: uuid.UUID
) -> Optional[SupplierResponsePacket]:
    """Load the normalized SupplierResponsePacket for a participant on this RFQ."""
    resp_result = await db.execute(
        select(SupplierResponse).where(
            SupplierResponse.rfq_id == rfq_id,
            SupplierResponse.participant_id == participant_id,
        )
    )
    resp = resp_result.scalar_one_or_none()
    if not resp:
        return None
    pkt_result = await db.execute(
        select(SupplierResponsePacket).where(
            SupplierResponsePacket.supplier_response_id == resp.id
        )
    )
    return pkt_result.scalar_one_or_none()


async def build_gltg_input_from_order(
    db: AsyncSession,
    order: Order,
    rfq_id: Optional[uuid.UUID] = None,
) -> ApparelOrderInput:
    """
    Build a GLTG ApparelOrderInput from an abcdYi Order.

    Pulls participant nodes from:
    - SupplierResponsePackets on the winning RFQ (if rfq_id is provided)
    - ParticipantProfile baseline data for all matched participants

    Falls back to profile-level lead times when packet data is absent.
    """
    # Load form fields for quantity and required delivery date
    form_fields: dict = {}
    required_delivery: Optional[date] = None
    quantity = 0
    product_categories: list[str] = []

    if order.locked_form_version_id:
        version = await db.get(DynamicOrderFormVersion, order.locked_form_version_id)
        if version and version.fields:
            form_fields = version.fields
            quantity = int(form_fields.get("quantity") or 0)
            product_categories = form_fields.get("product_categories") or []
            rd = form_fields.get("required_delivery_date")
            if rd:
                try:
                    if isinstance(rd, str):
                        required_delivery = date.fromisoformat(rd[:10])
                    elif isinstance(rd, date):
                        required_delivery = rd
                except ValueError:
                    pass

    # Load current milestones for reforecasting
    ms_result = await db.execute(
        select(Milestone).where(Milestone.order_id == order.id)
    )
    milestones = list(ms_result.scalars().all())
    milestone_updates: list[dict] = [
        {
            "milestone_type": m.milestone_type,
            "status": m.status,
            "planned_date": m.planned_date.isoformat() if m.planned_date else None,
            "predicted_date": m.predicted_date.isoformat() if m.predicted_date else None,
            "actual_date": m.actual_date.isoformat() if m.actual_date else None,
        }
        for m in milestones
    ]

    # Identify the winning RFQ if not given: find the most recent sent RFQ for this project
    effective_rfq_id = rfq_id
    if effective_rfq_id is None:
        rfq_result = await db.execute(
            select(RFQ)
            .where(RFQ.project_id == order.project_id, RFQ.status == "SENT")
            .order_by(RFQ.created_at.desc())
            .limit(1)
        )
        rfq_row = rfq_result.scalar_one_or_none()
        if rfq_row:
            effective_rfq_id = rfq_row.id

    # Build participant nodes from supplier responses
    participant_nodes: list[ParticipantNode] = []

    if effective_rfq_id:
        # Load all responses for this RFQ
        responses_result = await db.execute(
            select(SupplierResponse).where(SupplierResponse.rfq_id == effective_rfq_id)
        )
        responses = list(responses_result.scalars().all())

        for resp in responses:
            pkt_result = await db.execute(
                select(SupplierResponsePacket).where(
                    SupplierResponsePacket.supplier_response_id == resp.id
                )
            )
            pkt = pkt_result.scalar_one_or_none()

            # Load participant role
            role_result = await db.execute(
                select(ParticipantRole).where(
                    ParticipantRole.participant_id == resp.participant_id,
                    ParticipantRole.is_active == True,
                )
            )
            role_row = role_result.scalars().first()
            role_name = _ROLE_MAP.get(role_row.role_name if role_row else "", "MANUFACTURER")

            # Load profile for baseline data
            profile_result = await db.execute(
                select(ParticipantProfile).where(
                    ParticipantProfile.participant_id == resp.participant_id
                )
            )
            profile = profile_result.scalar_one_or_none()

            node = ParticipantNode(
                participant_id=str(resp.participant_id),
                role=role_name,
                fabric_lead_time_days=pkt.fabric_lead_time_days if pkt else None,
                trim_lead_time_days=pkt.trim_lead_time_days if pkt else None,
                packaging_lead_time_days=pkt.packaging_time_days if pkt else None,
                production_time_days=pkt.production_time_days if pkt else None,
                qc_time_days=pkt.qc_time_days if pkt else None,
                logistics_time_days=pkt.logistics_time_days if pkt else None,
                supplier_stated_lead_time_days=pkt.total_lead_time_days if pkt else None,
                moq=pkt.moq if pkt else (profile.moq if profile else None),
                capacity_available=bool(pkt.capacity_available) if pkt and pkt.capacity_available is not None else None,
                unit_price=pkt.unit_price if pkt else None,
                currency=pkt.currency if pkt else None,
            )
            participant_nodes.append(node)

    return ApparelOrderInput(
        order_id=str(order.id),
        required_delivery_date=required_delivery,
        quantity=quantity,
        product_categories=product_categories if isinstance(product_categories, list) else [],
        participant_nodes=participant_nodes,
        milestone_updates=milestone_updates,
        form_fields=form_fields,
    )


def _node_risk_flags(node: ParticipantNode) -> list[str]:
    """Business-level risk flags derived from abcdYi participant reliability data.

    These are abcdYi's own supplier-reliability signals (not GLTG lead-time math).
    """
    flags: list[str] = []
    if node.capacity_available is False:
        flags.append("CAPACITY_CONSTRAINT")
    if node.quality_issue_count and node.quality_issue_count > 0:
        flags.append("QUALITY_ISSUES")
    if node.qc_pass_rate is not None and node.qc_pass_rate < 0.8:
        flags.append("QC_RISK")
    if node.on_time_delivery_rate is not None and node.on_time_delivery_rate < 0.85:
        flags.append("DELIVERY_RISK")
    return flags


def _node_missing_evidence(node: ParticipantNode) -> list[str]:
    missing: list[str] = []
    for fld in ("fabric_lead_time_days", "production_time_days", "qc_time_days", "logistics_time_days"):
        if getattr(node, fld) is None:
            missing.append(fld)
    return missing


def _node_to_supplier(node: ParticipantNode) -> dict:
    """Map an abcdYi participant node to a GLTG API supplier payload."""
    material = (
        (node.fabric_lead_time_days or 0)
        + (node.trim_lead_time_days or 0)
        + (node.packaging_lead_time_days or 0)
    )
    production = node.production_time_days or 0
    qc = node.qc_time_days or 0
    logistics = node.logistics_time_days or 0
    if material + production + qc + logistics == 0 and node.supplier_stated_lead_time_days:
        production = node.supplier_stated_lead_time_days
    confidence = node.on_time_delivery_rate if node.on_time_delivery_rate is not None else 0.5
    return {
        "supplier_id": node.participant_id,
        "name": node.participant_id,
        "material_ready_days": material,
        "production_days": production,
        "qc_days": qc,
        "logistics_days": logistics,
        "confidence": confidence,
    }


def _api_path_to_delivery_path(p: dict, node_by_id: dict[str, ParticipantNode]) -> DeliveryPath:
    sid = (p.get("supplier_ids") or [None])[0]
    node = node_by_id.get(sid)
    total = p.get("estimated_lead_time_days")
    total_int = int(round(total)) if total is not None else None
    earliest = p.get("earliest_delivery_date")
    earliest_d = date.fromisoformat(earliest) if isinstance(earliest, str) else None
    feasible = bool(p.get("feasible"))
    node_flags = _node_risk_flags(node) if node else []
    path_flags = node_flags + [w.get("code") for w in p.get("warnings", [])]
    return DeliveryPath(
        path_id=p.get("path_id", f"PATH-{sid}"),
        participant_ids=[sid] if sid else [],
        parallel_max_days=None,
        sequential_days=total_int,
        total_lead_time_days=total_int,
        earliest_delivery_date=earliest_d,
        most_likely_delivery_date=earliest_d,
        risk_adjusted_delivery_date=earliest_d,
        committable_delivery_date=earliest_d,
        critical_path=["material", "production", "qc", "logistics"],
        critical_path_days=total_int,
        is_feasible=feasible,
        feasibility_reason="FEASIBLE" if feasible else "INFEASIBLE",
        risk_flags=path_flags,
        missing_evidence=_node_missing_evidence(node) if node else [],
        unit_price=node.unit_price if node else None,
        currency=node.currency if node else None,
        rank_score=float(p.get("score") or 0.0),
        recommendation_reason=f"rank {p.get('rank')}",
        confidence="HIGH" if (p.get("confidence") or 0) >= 0.75 else "MEDIUM" if (p.get("confidence") or 0) >= 0.5 else "LOW",
    )


def evaluate_delivery_feasibility(
    gltg_input: ApparelOrderInput,
    client: GLTGClient | None = None,
) -> DeliveryFeasibilityPacket:
    """Evaluate feasibility via the standalone GLTG API and map to abcdYi DTOs."""
    client = client or GLTGClient()
    node_by_id = {n.participant_id: n for n in gltg_input.participant_nodes}
    suppliers = [_node_to_supplier(n) for n in gltg_input.participant_nodes]

    order: dict = {
        "product_type": (gltg_input.product_categories or ["apparel"])[0] if gltg_input.product_categories else "apparel",
        "quantity": gltg_input.quantity or int(gltg_input.form_fields.get("quantity") or 0),
    }
    if gltg_input.required_delivery_date:
        order["target_delivery_date"] = gltg_input.required_delivery_date.isoformat()

    est = client.estimate_lead_time(order=order, suppliers=suppliers, constraints={})
    if not est.ok or est.data is None:
        raise GLTGUnavailableError(est.error or "GLTG estimate failed")
    paths_res = client.enumerate_paths(order=order, suppliers=suppliers, constraints={})
    if not paths_res.ok or paths_res.data is None:
        raise GLTGUnavailableError(paths_res.error or "GLTG path enumeration failed")

    data = est.data
    ranked = [
        _api_path_to_delivery_path(p, node_by_id)
        for p in paths_res.data.get("paths", [])
        if p.get("mode") == "SINGLE_SOURCE"
    ]
    # Never present more than 3 options (product rule; never faked).
    ranked = ranked[:3]

    earliest = data.get("earliest_delivery_date")
    earliest_d = date.fromisoformat(earliest) if isinstance(earliest, str) else None
    risk_flags = [w.get("code") for w in data.get("warnings", [])]
    # Aggregate abcdYi business risk flags + missing-evidence across nodes.
    missing_evidence: list[str] = []
    for node in gltg_input.participant_nodes:
        for f in _node_risk_flags(node):
            if f not in risk_flags:
                risk_flags.append(f)
        for m in _node_missing_evidence(node):
            if m not in missing_evidence:
                missing_evidence.append(m)
    feasible = data.get("feasible")
    if not suppliers:
        status = "INCOMPLETE_EVIDENCE"
        feasibility = "UNKNOWN"
    else:
        status = "EVALUATED"
        feasibility = "FEASIBLE" if feasible else "INFEASIBLE"

    days_vs_deadline = None
    if gltg_input.required_delivery_date and earliest_d:
        days_vs_deadline = (earliest_d - gltg_input.required_delivery_date).days

    confidence = "HIGH" if (data.get("risk_level") == "low") else "MEDIUM" if data.get("risk_level") == "medium" else "LOW"

    return DeliveryFeasibilityPacket(
        order_id=gltg_input.order_id,
        source="GLTG",
        status=status,
        earliest_delivery_date=earliest_d,
        most_likely_delivery_date=earliest_d,
        risk_adjusted_delivery_date=earliest_d,
        committable_delivery_date=earliest_d,
        required_delivery_date=gltg_input.required_delivery_date,
        delivery_feasibility=feasibility,
        days_vs_deadline=days_vs_deadline,
        critical_path=["material", "production", "qc", "logistics"] if suppliers else [],
        critical_path_days=int(round(data["estimated_lead_time_days"])) if data.get("estimated_lead_time_days") is not None else None,
        ranked_options=ranked,
        option_count=len(ranked),
        risk_flags=risk_flags,
        missing_evidence=missing_evidence,
        explanation=(
            f"GLTG evaluated {len(ranked)} path(s) via the standalone service; "
            f"feasibility={feasibility}, risk={data.get('risk_level')}."
        ),
        confidence=confidence,
    )
