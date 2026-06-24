from __future__ import annotations

from datetime import datetime, timezone

from src.gpm.api.schemas import ApprovalRecord
from src.gpm.models.gpm_quote_guidance_packet import GPMQuoteGuidancePacket


class GPMApprovalService:
    def record_approval(
        self,
        *,
        packet: GPMQuoteGuidancePacket,
        operator_id: str,
        approval_note: str = "",
        selected_option_id: str | None = None,
    ) -> ApprovalRecord:
        packet.approval_status = "approved"
        return ApprovalRecord(
            packet_id=packet.packet_id,
            operator_id=operator_id,
            approval_status="approved",
            approval_note=approval_note,
            selected_option_id=selected_option_id,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            dispatched=False,
            dispatch_note="No external action taken.",
        )

    def record_rejection(
        self,
        *,
        packet: GPMQuoteGuidancePacket,
        operator_id: str,
        approval_note: str = "",
    ) -> ApprovalRecord:
        packet.approval_status = "rejected"
        return ApprovalRecord(
            packet_id=packet.packet_id,
            operator_id=operator_id,
            approval_status="rejected",
            approval_note=approval_note,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            dispatched=False,
            dispatch_note="No external action taken.",
        )
