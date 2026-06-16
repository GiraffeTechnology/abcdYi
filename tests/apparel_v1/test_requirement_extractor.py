"""Unit tests for the requirement extraction module."""
import pytest
from src.apparel_v1.inquiry_intake import intake_inquiry, CANONICAL_INQUIRY
from src.apparel_v1.requirement_extractor import extract_requirements, ExtractedRequirements


class TestExtractRequirements:
    def setup_method(self):
        self.inquiry = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(self.inquiry)

    def test_returns_extracted_requirements(self):
        assert isinstance(self.req, ExtractedRequirements)

    def test_inquiry_id_linked(self):
        assert self.req.inquiry_id == self.inquiry.inquiry_id

    def test_quantity_extracted(self):
        assert self.req.quantity == 10000

    def test_product_type_extracted(self):
        assert self.req.product_type is not None
        assert "shirt" in self.req.product_type.lower()

    def test_fabric_type_extracted(self):
        assert self.req.fabric_type is not None
        assert "cotton" in self.req.fabric_type.lower()

    def test_color_extracted(self):
        assert self.req.color is not None
        assert "white" in self.req.color.lower()
        assert "light blue" in self.req.color.lower()

    def test_size_range_extracted(self):
        assert self.req.size_range == "S/M/L/XL"

    def test_size_breakdown_generated(self):
        assert self.req.size_breakdown is not None
        assert sum(self.req.size_breakdown.values()) == 10000

    def test_delivery_deadline_days_extracted(self):
        assert self.req.delivery_deadline_days == 45

    def test_trade_term_extracted(self):
        assert self.req.trade_term == "FOB"

    def test_destination_extracted(self):
        assert self.req.destination is not None
        assert "china" in self.req.destination.lower()

    def test_target_market_extracted(self):
        assert self.req.target_market == "Japan"

    def test_qc_standard_defaulted(self):
        assert self.req.qc_standard == "AQL 2.5"

    def test_ai_generated_flag(self):
        assert self.req.ai_generated is True

    def test_extraction_id_assigned(self):
        assert self.req.extraction_id.startswith("EXT-")

    def test_deterministic_same_result(self):
        req2 = extract_requirements(self.inquiry)
        assert req2.quantity == self.req.quantity
        assert req2.fabric_type == self.req.fabric_type
        assert req2.delivery_deadline_days == self.req.delivery_deadline_days

    def test_custom_polyester_inquiry(self):
        inq = intake_inquiry("5000 polyester jackets, navy, M-XXL, within 60 days, FOB Shanghai")
        req = extract_requirements(inq)
        assert req.quantity == 5000
        assert "polyester" in req.fabric_type.lower()
        assert req.delivery_deadline_days == 60
        assert req.trade_term == "FOB"
