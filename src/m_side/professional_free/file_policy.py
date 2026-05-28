"""
File Policy for Professional Free tier.
Explicitly disables all encryption and Enterprise CAP features.
"""

from typing import Literal
from pydantic import BaseModel

from src.m_side.m_event_logger import log_m_event

PROFESSIONAL_FREE_WARNING_TEXT = (
    "Professional Free does not provide encrypted file protection or Enterprise CAP. "
    "Do not upload highly confidential CAD / STEP / BOM files. "
    "Use Enterprise CAP for confidential engineering documents."
)


class FilePolicy(BaseModel):
    product_tier: Literal["professional_free"] = "professional_free"
    encryption_enabled: bool = False
    dynamic_watermark_enabled: bool = False
    secure_viewer_enabled: bool = False
    local_storage_allowed: bool = True
    mock_file_refs_allowed: bool = True
    audit_log_enabled: bool = True
    user_warning_required: bool = True
    warning_text: str = PROFESSIONAL_FREE_WARNING_TEXT


def get_professional_free_file_policy() -> FilePolicy:
    return FilePolicy()


def show_file_warning(project_id: str, actor_id: str) -> str:
    """Show the Professional Free file confidentiality warning and log the event."""
    policy = get_professional_free_file_policy()
    log_m_event(
        event_type="PROFESSIONAL_FREE_FILE_WARNING_SHOWN",
        b_workspace_id=project_id,
        supplier_id=actor_id,
        payload={
            "warning_text": policy.warning_text,
            "encryption_enabled": policy.encryption_enabled,
            "secure_viewer_enabled": policy.secure_viewer_enabled,
        },
    )
    return policy.warning_text


def acknowledge_cap_limitation(project_id: str, actor_id: str) -> None:
    log_m_event(
        event_type="PROFESSIONAL_FREE_CAP_LIMITATION_ACKNOWLEDGED",
        b_workspace_id=project_id,
        supplier_id=actor_id,
        payload={"tier": "professional_free"},
    )
