"""M-side logistics handover request and IM message handling."""
from src.m_side.m_event_logger import log_m_event


def request_logistics_handover(project_id: str, supplier_actor_id: str) -> dict:
    msg = (
        "订单已到物流交接阶段。请回复物流公司、运单号，并上传面单照片。\n"
        "例如：已发顺丰，单号 SF123456789，今天下午发出。\n\n"
        "The order has reached logistics handover. Please reply with the carrier name, "
        "tracking number, and upload a shipping label photo.\n"
        "Example: Shipped via SF Express, tracking SF123456789."
    )
    log_m_event(
        event_type="LOGISTICS_HANDOVER_REQUESTED",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"message": msg},
    )
    return {"status": "requested", "message": msg}


def log_logistics_handover_received(project_id: str, supplier_actor_id: str, raw_message: str) -> dict:
    log_m_event(
        event_type="LOGISTICS_HANDOVER_RECEIVED",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"raw_message": raw_message[:200]},
    )
    return {"status": "received", "raw_message": raw_message}
