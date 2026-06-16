"""
B-side inquiry intake for the apparel/textile v1 E2E flow.
Accepts raw buyer inquiry text and produces a structured BuyerInquiry record.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


CANONICAL_INQUIRY = (
    "I need 10,000 cotton shirts for export. "
    "White and light blue, mixed sizes S/M/L/XL, "
    "delivery within 45 days, FOB China, target market Japan."
)


@dataclass
class BuyerInquiry:
    raw_text: str
    inquiry_id: str = field(default_factory=lambda: f"INQ-{uuid.uuid4().hex[:8].upper()}")
    channel: str = "direct"
    buyer_id: str = "BUYER-001"
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def intake_inquiry(
    raw_text: str,
    channel: str = "direct",
    buyer_id: str = "BUYER-001",
) -> BuyerInquiry:
    """
    Intake a raw buyer inquiry text and return a structured BuyerInquiry record.
    Validates that text is non-empty; strips whitespace.
    """
    text = raw_text.strip()
    if not text:
        raise ValueError("Inquiry text must not be empty")
    return BuyerInquiry(
        raw_text=text,
        channel=channel,
        buyer_id=buyer_id,
    )
