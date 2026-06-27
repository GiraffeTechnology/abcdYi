"""Single entry point for GLTG-based delivery feasibility evaluation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.lead_time.gltg_models import DeliveryFeasibilityPacket as GltgPacket, DeliveryPath

from src.db.models.delivery_feasibility import DeliveryFeasibilityPacketRecord
from src.db.models.order import Order
from src.lead_time.gltg_adapter import build_gltg_input_from_order, evaluate_delivery_feasibility
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import DELIVERY_FEASIBILITY_EVALUATED


def _path_to_dict(path: DeliveryPath) -> dict:
    return {
        "path_id": path.path_id,
        "participant_ids": path.participant_ids,
        "parallel_max_days": path.parallel_max_days,
        "sequential_days": path.sequential_days,
        "total_lead_time_days": path.total_lead_time_days,
        "earliest_delivery_date": path.earliest_delivery_date.isoformat() if path.earliest_delivery_date else None,
        "most_likely_delivery_date": path.most_likely_delivery_date.isoformat() if path.most_likely_delivery_date else None,
        "risk_adjusted_delivery_date": path.risk_adjusted_delivery_date.isoformat() if path.risk_adjusted_delivery_date else None,
        "committable_delivery_date": path.committable_delivery_date.isoformat() if path.committable_delivery_date else None,
        "critical_path": path.critical_path,
        "critical_path_days": path.critical_path_days,
        "is_feasible": path.is_feasible,
        "feasibility_reason": path.feasibility_reason,
        "risk_flags": path.risk_flags,
        "missing_evidence": path.missing_evidence,
        "unit_price": path.unit_price,
        "currency": path.currency,
        "rank_score": path.rank_score,
        "recommendation_reason": path.recommendation_reason,
        "confidence": path.confidence,
    }


def _packet_to_dict(packet: GltgPacket) -> dict:
    return {
        "order_id": packet.order_id,
        "source": packet.source,
        "status": packet.status,
        "earliest_delivery_date": packet.earliest_delivery_date.isoformat() if packet.earliest_delivery_date else None,
        "most_likely_delivery_date": packet.most_likely_delivery_date.isoformat() if packet.most_likely_delivery_date else None,
        "risk_adjusted_delivery_date": packet.risk_adjusted_delivery_date.isoformat() if packet.risk_adjusted_delivery_date else None,
        "committable_delivery_date": packet.committable_delivery_date.isoformat() if packet.committable_delivery_date else None,
        "required_delivery_date": packet.required_delivery_date.isoformat() if packet.required_delivery_date else None,
        "delivery_feasibility": packet.delivery_feasibility,
        "days_vs_deadline": packet.days_vs_deadline,
        "critical_path": packet.critical_path,
        "critical_path_days": packet.critical_path_days,
        "ranked_options": [_path_to_dict(p) for p in packet.ranked_options],
        "option_count": packet.option_count,
        "risk_flags": packet.risk_flags,
        "missing_evidence": packet.missing_evidence,
        "explanation": packet.explanation,
        "confidence": packet.confidence,
    }


class DeliveryFeasibilityService:

    async def evaluate(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        rfq_id: Optional[uuid.UUID] = None,
        triggered_by_user_id: Optional[uuid.UUID] = None,
    ) -> DeliveryFeasibilityPacketRecord:
        """
        Evaluate delivery feasibility for an order using GLTG.
        Persists the result to delivery_feasibility_packets and emits an execution event.
        Returns the persisted record.
        """
        order = await db.get(Order, order_id)
        if not order:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Order not found")

        effective_project_id = project_id or order.project_id

        # Build GLTG input and run evaluation (synchronous engine)
        gltg_input = await build_gltg_input_from_order(db, order, rfq_id=rfq_id)
        packet: GltgPacket = evaluate_delivery_feasibility(gltg_input)

        # Serialise ranked options (up to 3, never faked)
        ranked_dicts = [_path_to_dict(p) for p in packet.ranked_options]

        record = DeliveryFeasibilityPacketRecord(
            tenant_id=tenant_id,
            project_id=effective_project_id,
            order_id=order_id,
            source=packet.source,
            status=packet.status,
            earliest_delivery_date=packet.earliest_delivery_date,
            most_likely_delivery_date=packet.most_likely_delivery_date,
            risk_adjusted_delivery_date=packet.risk_adjusted_delivery_date,
            committable_delivery_date=packet.committable_delivery_date,
            required_delivery_date=packet.required_delivery_date,
            delivery_feasibility=packet.delivery_feasibility,
            days_vs_deadline=packet.days_vs_deadline,
            critical_path_json=packet.critical_path,
            critical_path_days=packet.critical_path_days,
            ranked_options_json=ranked_dicts,
            option_count=packet.option_count,
            risk_flags_json=packet.risk_flags,
            missing_evidence_json=packet.missing_evidence,
            raw_gltg_packet_json=_packet_to_dict(packet),
            explanation=packet.explanation,
            confidence=packet.confidence,
        )
        db.add(record)
        await db.flush()

        await emit_event(
            db=db,
            event_type=DELIVERY_FEASIBILITY_EVALUATED,
            payload={
                "feasibility_packet_id": str(record.id),
                "order_id": str(order_id),
                "delivery_feasibility": packet.delivery_feasibility,
                "option_count": packet.option_count,
                "confidence": packet.confidence,
            },
            tenant_id=tenant_id,
            project_id=effective_project_id,
            order_id=order_id,
            triggered_by_user_id=triggered_by_user_id,
        )

        return record
