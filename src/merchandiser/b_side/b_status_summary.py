"""B-side order status summary."""
from src.merchandiser.b_side.b_merchandiser_service import send_b_side_status_update


def send_order_status_summary(project_id: str, buyer_actor_id: str, order_state: str, detail: str = "") -> dict:
    msg = f"Your order is now in state: {order_state.replace('_', ' ').title()}. {detail}".strip()
    return send_b_side_status_update(project_id, buyer_actor_id, msg)
