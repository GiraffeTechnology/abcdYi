"""
M-side OpenClaw response formatter.
"""

from src.core_schema.m_side_types import (
    MSideWorkspace,
    SupplierResponsePacket,
    OrderExecutionContext,
)


def format_m_workspace(workspace: MSideWorkspace) -> dict:
    """Format MSideWorkspace for API response."""
    return workspace.model_dump(mode="json")


def format_response_packet_preview(packet: SupplierResponsePacket) -> dict:
    """Format a compact response packet preview for supplier confirmation."""
    return {
        "supplier_name": packet.supplier_name,
        "can_make": packet.capacity_signal.can_make,
        "lead_time_days": packet.schedule_signal.estimated_lead_time_days,
        "unit_price": packet.quote.unit_price,
        "currency": packet.quote.currency,
        "material_available": packet.material_availability.material_available,
        "qc_available": packet.qc_commitment.qc_available,
        "logistics_notes": packet.logistics_commitment.logistics_notes,
        "red_flags": packet.red_flags,
        "completeness_score": packet.completeness_score,
        "confidence_score": packet.confidence_score,
        "summary": packet.supplier_summary_for_buyer,
    }


def format_order_execution(order: OrderExecutionContext) -> dict:
    """Format OrderExecutionContext for API response."""
    return order.model_dump(mode="json")
