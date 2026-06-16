"""Unit tests for the mock supplier response simulator."""
import pytest
from src.apparel_v1.inquiry_intake import intake_inquiry, CANONICAL_INQUIRY
from src.apparel_v1.requirement_extractor import extract_requirements
from src.apparel_v1.supplier_response_simulator import (
    simulate_supplier_responses,
    MockSupplierResponse,
)


class TestSimulateSupplierResponses:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        self.responses = simulate_supplier_responses(self.req)

    def test_returns_three_responses(self):
        assert len(self.responses) == 3

    def test_returns_mock_supplier_response_objects(self):
        assert all(isinstance(r, MockSupplierResponse) for r in self.responses)

    def test_profiles_are_fast_cheap_balanced(self):
        profiles = {r.profile for r in self.responses}
        assert profiles == {"fast", "cheap", "balanced"}

    def test_all_have_unique_response_ids(self):
        ids = [r.response_id for r in self.responses]
        assert len(ids) == len(set(ids))

    def test_all_have_positive_prices(self):
        for r in self.responses:
            assert r.unit_price_usd > 0
            assert r.total_price_usd > 0

    def test_total_price_equals_unit_times_quantity(self):
        qty = self.req.quantity or 10000
        for r in self.responses:
            expected = round(r.unit_price_usd * qty, 2)
            assert abs(r.total_price_usd - expected) < 0.01

    def test_all_have_positive_lead_times(self):
        for r in self.responses:
            assert r.supplier_stated_total_days > 0
            assert r.production_days > 0
            assert r.fabric_days > 0

    def test_fast_supplier_is_fastest(self):
        fast = next(r for r in self.responses if r.profile == "fast")
        cheap = next(r for r in self.responses if r.profile == "cheap")
        assert fast.supplier_stated_total_days < cheap.supplier_stated_total_days

    def test_cheap_supplier_is_cheapest(self):
        fast = next(r for r in self.responses if r.profile == "fast")
        cheap = next(r for r in self.responses if r.profile == "cheap")
        assert cheap.unit_price_usd < fast.unit_price_usd

    def test_all_have_supplier_names(self):
        for r in self.responses:
            assert r.supplier_name
            assert r.supplier_id

    def test_all_have_locations(self):
        for r in self.responses:
            assert "China" in r.location

    def test_confidence_scores_in_range(self):
        for r in self.responses:
            assert 0.0 <= r.confidence_score <= 1.0
            assert 0.0 <= r.completeness_score <= 1.0

    def test_currency_is_usd(self):
        for r in self.responses:
            assert r.currency == "USD"
