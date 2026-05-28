"""M-side upstream/subcontractor follow-up."""
from src.m_side.m_event_logger import log_m_event


def send_upstream_followup(
    project_id: str,
    supplier_actor_id: str,
    upstream_actor_id: str,
    dependency_type: str,
) -> dict:
    msg = f"请确认 {dependency_type.replace('_', ' ')} 的进度和交货时间。"
    log_m_event(
        event_type="M_UPSTREAM_FOLLOWUP_SENT",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"upstream_actor_id": upstream_actor_id, "dependency_type": dependency_type},
    )
    return {"status": "sent", "message": msg}
