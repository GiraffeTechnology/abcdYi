"""Routes merchandiser events to B-side and M-side messages."""
from src.m_side.m_event_logger import log_m_event


def route_merchandiser_message(
    project_id: str,
    actor_id: str,
    event_or_task: dict,
) -> dict:
    event_type = event_or_task.get("event_type") or event_or_task.get("task_type", "")
    side = event_or_task.get("assigned_side", "B_SIDE")

    if side == "B_SIDE" or "buyer" in event_type.lower():
        msg = _build_b_side_message(event_type, event_or_task)
        log_m_event(
            event_type="B_SIDE_STATUS_UPDATE_SENT",
            b_workspace_id=project_id,
            supplier_id=actor_id,
            payload={"message": msg[:120]},
        )
        return {"side": "B_SIDE", "message": msg}
    else:
        msg = _build_m_side_message(event_type, event_or_task)
        log_m_event(
            event_type="M_SIDE_PROGRESS_CHECK_REQUESTED",
            b_workspace_id=project_id,
            supplier_id=actor_id,
            payload={"message": msg[:120]},
        )
        return {"side": "M_SIDE", "message": msg}


def _build_b_side_message(event_type: str, context: dict) -> str:
    if "material_delay" in event_type or "material_shortage" in event_type:
        return (
            "The supplier reported a fabric delay. Two options are available: "
            "wait 3 extra days or switch to backup fabric."
        )
    if "milestone" in event_type:
        milestone_type = context.get("milestone_type", "")
        return (
            f"Milestone confirmation required: {milestone_type.replace('_', ' ').title()}. "
            "Please review and confirm."
        )
    if "logistics" in event_type:
        tracking = context.get("tracking_number", "")
        return f"Logistics update: Tracking {tracking} has been updated."
    return f"Order update: {event_type.replace('_', ' ').title()}."


def _build_m_side_message(event_type: str, context: dict) -> str:
    if "material_delay" in event_type or "material_shortage" in event_type:
        return "请确认是否采用备用布料方案，或继续等待原布料。若影响交期，请说明新的预计完成时间。"
    if "milestone" in event_type:
        return "请更新生产进度并上传照片。"
    if "logistics" in event_type:
        return "请提供物流公司和运单号信息。"
    return f"请更新当前状态：{event_type.replace('_', ' ')}。"
