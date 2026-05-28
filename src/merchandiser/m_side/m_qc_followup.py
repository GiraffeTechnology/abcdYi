"""M-side QC follow-up."""
from src.m_side.m_event_logger import log_m_event


def request_qc_update(project_id: str, supplier_actor_id: str, stage: str = "final_qc") -> dict:
    msg = f"请上传 {stage.replace('_', ' ')} 检验报告和合格证明。"
    log_m_event(
        event_type="M_QC_UPDATE_REQUESTED",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"stage": stage, "message": msg},
    )
    return {"status": "requested", "message": msg}
