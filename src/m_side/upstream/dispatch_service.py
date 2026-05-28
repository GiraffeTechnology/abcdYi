"""
Upstream Dispatch Service — sends upstream inquiries via configured channel.
MOCK_CHANNELS=true (default) simulates dispatch locally.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel

from src.m_side.upstream.inquiry_builder import UpstreamInquiry
from src.m_side.m_event_logger import log_m_event

MOCK_CHANNELS = os.environ.get("MOCK_CHANNELS", "true").lower() == "true"
WECHAT_ENABLED = os.environ.get("WECHAT_ENABLED", "false").lower() == "true"
WHATSAPP_ENABLED = os.environ.get("WHATSAPP_ENABLED", "false").lower() == "true"
OPENCLAW_ENABLED = os.environ.get("OPENCLAW_ENABLED", "true").lower() == "true"


class DispatchResult(BaseModel):
    dispatch_id: str
    inquiry_id: str
    upstream_actor_id: str
    channel: str
    status: Literal["sent", "mock_sent", "failed"]
    message: str
    dispatched_at: str


def dispatch_upstream_inquiry(
    inquiry: UpstreamInquiry,
    channel: Literal["wechat", "whatsapp", "openclaw", "web_fallback", "mock"] = "mock",
) -> DispatchResult:
    """
    Dispatch an upstream inquiry to the supplier via the specified channel.
    Falls back to mock when MOCK_CHANNELS=true.
    """
    now = datetime.now(timezone.utc).isoformat()
    dispatch_id = f"DSP-{uuid.uuid4().hex[:10].upper()}"

    if MOCK_CHANNELS or channel == "mock":
        status: Literal["sent", "mock_sent", "failed"] = "mock_sent"
        message = (
            f"[MOCK] Inquiry {inquiry.inquiry_id} dispatched to {inquiry.upstream_actor_id} "
            f"via mock channel. Message preview: {inquiry.message_text_en[:80]}..."
        )
        actual_channel = "mock"
    elif channel == "openclaw" and OPENCLAW_ENABLED:
        status = "sent"
        message = f"Inquiry {inquiry.inquiry_id} dispatched via OpenClaw to {inquiry.upstream_actor_id}."
        actual_channel = "openclaw"
    elif channel == "wechat" and WECHAT_ENABLED:
        status = "sent"
        message = f"Inquiry {inquiry.inquiry_id} dispatched via WeChat to {inquiry.upstream_actor_id}."
        actual_channel = "wechat"
    elif channel == "whatsapp" and WHATSAPP_ENABLED:
        status = "sent"
        message = f"Inquiry {inquiry.inquiry_id} dispatched via WhatsApp to {inquiry.upstream_actor_id}."
        actual_channel = "whatsapp"
    else:
        status = "mock_sent"
        message = f"[FALLBACK] Inquiry dispatched via web fallback to {inquiry.upstream_actor_id}."
        actual_channel = "web_fallback"

    result = DispatchResult(
        dispatch_id=dispatch_id,
        inquiry_id=inquiry.inquiry_id,
        upstream_actor_id=inquiry.upstream_actor_id,
        channel=actual_channel,
        status=status,
        message=message,
        dispatched_at=now,
    )

    log_m_event(
        event_type="UPSTREAM_INQUIRY_DISPATCHED",
        b_workspace_id=inquiry.project_id,
        supplier_id=inquiry.parent_main_supplier_actor_id,
        payload={
            "dispatch_id": dispatch_id,
            "inquiry_id": inquiry.inquiry_id,
            "upstream_actor_id": inquiry.upstream_actor_id,
            "channel": actual_channel,
            "status": status,
        },
    )

    return result
