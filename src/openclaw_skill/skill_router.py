"""
OpenClaw skill router — routes action names to handler functions.
Supports both B-side and M-side actions.
"""

from src.openclaw_skill.m_side_actions import (
    handle_m_side_receive_inquiry,
    handle_m_side_submit_supplier_response,
    handle_m_side_get_pending_question,
    handle_m_side_submit_order_acknowledgement,
    handle_m_side_submit_production_update,
    handle_m_side_submit_qc_update,
    handle_m_side_submit_logistics_update,
    handle_m_side_report_exception,
)
from src.openclaw_skill.response_formatter import format_error

_ACTION_HANDLERS = {
    # M-side actions
    "m_side_receive_inquiry": handle_m_side_receive_inquiry,
    "m_side_submit_supplier_response": handle_m_side_submit_supplier_response,
    "m_side_get_pending_question": handle_m_side_get_pending_question,
    "m_side_submit_order_acknowledgement": handle_m_side_submit_order_acknowledgement,
    "m_side_submit_production_update": handle_m_side_submit_production_update,
    "m_side_submit_qc_update": handle_m_side_submit_qc_update,
    "m_side_submit_logistics_update": handle_m_side_submit_logistics_update,
    "m_side_report_exception": handle_m_side_report_exception,
}


def route_action(action: str, params: dict) -> dict:
    """Route an action name to the appropriate handler. Returns formatted response."""
    handler = _ACTION_HANDLERS.get(action)
    if handler is None:
        return format_error(f"Unknown action: {action}", code="UNKNOWN_ACTION")
    try:
        return handler(params)
    except Exception as e:
        return format_error(f"Action {action} failed: {str(e)}", code="ACTION_ERROR")
