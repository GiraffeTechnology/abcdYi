"""
Approval Gate — manages upstream option approval workflow.
Default: human approval required.
AUTO_APPROVAL_ENABLED=true allows authorized agent approval for low-risk options.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

from src.m_side.upstream.option_engine import UpstreamOption
from src.m_side.m_event_logger import log_m_event

AUTO_APPROVAL_ENABLED = os.environ.get("AUTO_APPROVAL_ENABLED", "false").lower() == "true"


class ApprovalRequest(BaseModel):
    approval_request_id: str
    project_id: str
    dependency_id: str
    dependency_type: str
    options: list[UpstreamOption]
    status: Literal["pending", "approved", "rejected"] = "pending"
    required_approval_mode: Literal["human", "authorized_agent"]
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ApprovalResult(BaseModel):
    approval_request_id: str
    approved_option_id: str
    approved_option: UpstreamOption
    approved_by: str
    mode: Literal["human", "authorized_agent"]
    approved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""


def request_upstream_option_approval(
    project_id: str,
    dependency_id: str,
    dependency_type: str,
    options: list[UpstreamOption],
) -> ApprovalRequest:
    """
    Create an approval request for upstream options.
    Medium/high-risk options always require human approval.
    """
    # Determine required approval mode
    has_high_risk = any(
        "long_lead_time" in f or "cannot_supply" in f or "price_not_confirmed" in f
        for opt in options
        for f in opt.risk_summary.lower().split(";")
    )

    if has_high_risk or not AUTO_APPROVAL_ENABLED:
        required_mode: Literal["human", "authorized_agent"] = "human"
    else:
        required_mode = "authorized_agent"

    request = ApprovalRequest(
        approval_request_id=f"APR-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        dependency_id=dependency_id,
        dependency_type=dependency_type,
        options=options,
        required_approval_mode=required_mode,
    )

    log_m_event(
        event_type="UPSTREAM_OPTION_APPROVAL_REQUESTED",
        b_workspace_id=project_id,
        payload={
            "approval_request_id": request.approval_request_id,
            "dependency_id": dependency_id,
            "dependency_type": dependency_type,
            "option_count": len(options),
            "required_approval_mode": required_mode,
        },
    )

    return request


def approve_upstream_option(
    approval_request: ApprovalRequest,
    approved_option_id: str,
    approved_by: str,
    mode: Literal["human", "authorized_agent"] = "human",
    notes: str = "",
) -> ApprovalResult:
    """
    Approve one upstream option from a pending approval request.
    Raises ValueError if trying to use authorized_agent when human is required.
    """
    if approval_request.required_approval_mode == "human" and mode == "authorized_agent":
        raise ValueError(
            f"Approval request {approval_request.approval_request_id} requires human approval. "
            f"Authorized agent approval not permitted for this option set."
        )

    approved_option = None
    for opt in approval_request.options:
        if opt.option_id == approved_option_id:
            approved_option = opt
            break

    if approved_option is None:
        raise ValueError(f"Option {approved_option_id} not found in approval request.")

    approval_request.status = "approved"

    result = ApprovalResult(
        approval_request_id=approval_request.approval_request_id,
        approved_option_id=approved_option_id,
        approved_option=approved_option,
        approved_by=approved_by,
        mode=mode,
        notes=notes,
    )

    log_m_event(
        event_type="UPSTREAM_OPTION_APPROVED",
        b_workspace_id=approval_request.project_id,
        supplier_id=approved_by,
        payload={
            "approval_request_id": approval_request.approval_request_id,
            "approved_option_id": approved_option_id,
            "approved_option_label": approved_option.option_label,
            "upstream_actor_id": approved_option.upstream_actor_id,
            "dependency_type": approved_option.dependency_type,
            "mode": mode,
            "approved_by": approved_by,
        },
    )

    return result
