"""M-side progress check requests to suppliers."""
from src.merchandiser.m_side.m_merchandiser_service import send_m_side_progress_check, receive_m_side_progress_update


def request_progress_update(project_id: str, supplier_actor_id: str, stage: str) -> dict:
    return send_m_side_progress_check(project_id, supplier_actor_id, stage)


def log_progress_update(project_id: str, supplier_actor_id: str, update_text: str) -> dict:
    return receive_m_side_progress_update(project_id, supplier_actor_id, update_text)
