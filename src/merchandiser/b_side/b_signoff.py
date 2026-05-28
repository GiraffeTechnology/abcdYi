"""B-side buyer sign-off after delivery."""
from src.m_side.m_event_logger import log_m_event


def request_buyer_signoff(project_id: str, buyer_actor_id: str, tracking_number: str) -> dict:
    msg = (
        f"The shipment ({tracking_number}) has been marked as delivered. "
        "Please confirm receipt:\n"
        "A. Confirm received\n"
        "B. Not received\n"
        "C. Received with issue"
    )
    log_m_event(
        event_type="BUYER_SIGNOFF_REQUESTED",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={"tracking_number": tracking_number, "message": msg},
    )
    return {"status": "signoff_requested", "message": msg}


def receive_buyer_signoff(
    project_id: str,
    buyer_actor_id: str,
    response: str = "confirmed",
    notes: str = "",
) -> dict:
    log_m_event(
        event_type="BUYER_SIGNOFF_RECEIVED",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={"response": response, "notes": notes},
    )
    return {"status": "signoff_received", "response": response}
