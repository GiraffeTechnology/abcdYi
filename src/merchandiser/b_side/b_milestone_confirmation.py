"""B-side milestone review request and confirmation."""
from src.m_side.m_event_logger import log_m_event


def send_milestone_review_request(
    project_id: str,
    buyer_actor_id: str,
    milestone_id: str,
    milestone_type: str,
    media_count: int,
) -> dict:
    msg = (
        f"Milestone confirmation required: {milestone_type.replace('_', ' ').title()}.\n"
        f"The supplier uploaded {media_count} photo(s).\n"
        "Reply:\nA. Confirm\nB. Request more photos\nC. Raise issue"
    )
    log_m_event(
        event_type="ORDER_MILESTONE_BUYER_REVIEW_PENDING",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={"milestone_id": milestone_id, "milestone_type": milestone_type, "message": msg},
    )
    return {"status": "review_requested", "message": msg}
