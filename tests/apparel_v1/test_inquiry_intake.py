"""Unit tests for B-side inquiry intake."""
import pytest
from src.apparel_v1.inquiry_intake import intake_inquiry, BuyerInquiry, CANONICAL_INQUIRY


class TestIntakeInquiry:
    def test_returns_buyer_inquiry(self):
        result = intake_inquiry(CANONICAL_INQUIRY)
        assert isinstance(result, BuyerInquiry)

    def test_inquiry_id_assigned(self):
        result = intake_inquiry(CANONICAL_INQUIRY)
        assert result.inquiry_id.startswith("INQ-")
        assert len(result.inquiry_id) > 4

    def test_raw_text_preserved(self):
        result = intake_inquiry(CANONICAL_INQUIRY)
        assert result.raw_text == CANONICAL_INQUIRY

    def test_whitespace_stripped(self):
        result = intake_inquiry("  cotton shirts  ")
        assert result.raw_text == "cotton shirts"

    def test_default_channel(self):
        result = intake_inquiry(CANONICAL_INQUIRY)
        assert result.channel == "direct"

    def test_custom_channel(self):
        result = intake_inquiry(CANONICAL_INQUIRY, channel="email")
        assert result.channel == "email"

    def test_custom_buyer_id(self):
        result = intake_inquiry(CANONICAL_INQUIRY, buyer_id="BUYER-999")
        assert result.buyer_id == "BUYER-999"

    def test_received_at_set(self):
        result = intake_inquiry(CANONICAL_INQUIRY)
        assert result.received_at is not None
        assert "T" in result.received_at  # ISO format

    def test_unique_inquiry_ids(self):
        r1 = intake_inquiry(CANONICAL_INQUIRY)
        r2 = intake_inquiry(CANONICAL_INQUIRY)
        assert r1.inquiry_id != r2.inquiry_id

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="empty"):
            intake_inquiry("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            intake_inquiry("   ")
