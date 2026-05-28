"""
B+M Bridge — Response Bridge.
Converts M-side SupplierResponsePacket into B-side SupplierResponseRecord
and appends it to the B-side workspace.
"""

import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import SupplierResponsePacket
from src.core_schema.b_side_types import SupplierResponseRecord
from src.b_side.supplier_response_intake import intake_supplier_response
from src.b_side.workspace import get_b_workspace, save_b_workspace
from src.m_side.m_event_logger import log_m_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def push_supplier_response_to_b_side(response_packet: SupplierResponsePacket) -> dict:
    """
    Convert M-side SupplierResponsePacket into B-side SupplierResponseRecord
    and append it to the B-side workspace.

    After push:
    - Saves B-side workspace
    - Logs M_RESPONSE_ATTACHED_TO_B_WORKSPACE event
    - Optionally triggers feasibility recalculation if >= 2 responses
    """
    # Convert SupplierResponsePacket → SupplierResponseRecord
    record = SupplierResponseRecord(
        response_id=f"BR-{uuid.uuid4().hex[:8].upper()}",
        rfq_id=response_packet.rfq_id,
        b_workspace_id=response_packet.b_workspace_id,
        supplier_id=response_packet.supplier_id,
        supplier_name=response_packet.supplier_name,
        can_make=response_packet.capacity_signal.can_make,
        capacity_available=response_packet.capacity_signal.capacity_available,
        material_available=response_packet.material_availability.material_available,
        estimated_lead_time_days=response_packet.schedule_signal.estimated_lead_time_days,
        unit_price=response_packet.quote.unit_price,
        total_price=response_packet.quote.total_price,
        currency=response_packet.quote.currency,
        qc_available=response_packet.qc_commitment.qc_available,
        logistics_notes=response_packet.logistics_commitment.logistics_notes,
        red_flags=response_packet.red_flags,
        completeness_score=response_packet.completeness_score,
        confidence_score=response_packet.confidence_score,
        raw_response=" | ".join(response_packet.raw_supplier_messages),
        submitted_at=response_packet.submitted_at,
    )

    # Append to B-side workspace
    workspace = intake_supplier_response(
        b_workspace_id=response_packet.b_workspace_id,
        response=record,
    )

    # Log event
    log_m_event(
        event_type="M_RESPONSE_ATTACHED_TO_B_WORKSPACE",
        m_workspace_id=response_packet.m_workspace_id,
        b_workspace_id=response_packet.b_workspace_id,
        supplier_id=response_packet.supplier_id,
        rfq_id=response_packet.rfq_id,
        payload={
            "can_make": record.can_make,
            "lead_time_days": record.estimated_lead_time_days,
            "completeness_score": record.completeness_score,
            "total_responses": len(workspace.supplier_responses),
        },
    )

    return {
        "ok": True,
        "b_workspace_id": response_packet.b_workspace_id,
        "supplier_id": response_packet.supplier_id,
        "total_responses": len(workspace.supplier_responses),
        "can_make": record.can_make,
    }
