"""Unit tests for the option generator."""
import pytest
from src.apparel_v1.inquiry_intake import intake_inquiry, CANONICAL_INQUIRY
from src.apparel_v1.requirement_extractor import extract_requirements
from src.apparel_v1.supplier_response_simulator import simulate_supplier_responses
from src.apparel_v1.option_generator import generate_options, BuyerOption


class TestGenerateOptions:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        self.responses = simulate_supplier_responses(self.req)
        self.options = generate_options(
            supplier_responses=self.responses,
            quantity=10000,
            buyer_deadline_days=45,
        )

    def test_returns_three_options(self):
        assert len(self.options) == 3

    def test_returns_buyer_option_objects(self):
        assert all(isinstance(o, BuyerOption) for o in self.options)

    def test_labels_are_a_b_c(self):
        labels = [o.option_label for o in self.options]
        assert sorted(labels) == ["A", "B", "C"]

    def test_options_sorted_by_label(self):
        labels = [o.option_label for o in self.options]
        assert labels == ["A", "B", "C"]

    def test_option_a_is_fastest(self):
        opt_a = next(o for o in self.options if o.option_label == "A")
        opt_b = next(o for o in self.options if o.option_label == "B")
        assert opt_a.total_lead_time_days < opt_b.total_lead_time_days

    def test_option_b_is_cheapest(self):
        opt_a = next(o for o in self.options if o.option_label == "A")
        opt_b = next(o for o in self.options if o.option_label == "B")
        assert opt_b.total_price_usd < opt_a.total_price_usd

    def test_all_options_have_quantity(self):
        for o in self.options:
            assert o.quantity == 10000

    def test_all_options_have_positive_prices(self):
        for o in self.options:
            assert o.unit_price_usd > 0
            assert o.total_price_usd > 0

    def test_all_options_have_positive_lead_times(self):
        for o in self.options:
            assert o.total_lead_time_days > 0
            assert o.production_lead_time_days > 0

    def test_option_a_feasible_for_45d(self):
        opt_a = next(o for o in self.options if o.option_label == "A")
        assert opt_a.feasible_for_deadline is True

    def test_all_options_have_qc_milestones(self):
        for o in self.options:
            assert len(o.qc_milestone_plan) >= 4

    def test_qc_milestones_have_required_keys(self):
        for o in self.options:
            for ms in o.qc_milestone_plan:
                assert "milestone" in ms
                assert "day" in ms
                assert "standard" in ms

    def test_all_options_have_evidence_references(self):
        for o in self.options:
            assert len(o.evidence_references) > 0

    def test_all_options_have_dependency_summary(self):
        for o in self.options:
            assert o.supplier_dependency_summary
            assert len(o.supplier_dependency_summary) > 10

    def test_human_approval_defaults_to_pending(self):
        for o in self.options:
            assert o.human_approval_status == "pending"

    def test_slack_days_calculated(self):
        opt_a = next(o for o in self.options if o.option_label == "A")
        if opt_a.feasible_for_deadline:
            assert opt_a.slack_days is not None
            assert opt_a.slack_days >= 0

    def test_lead_time_path_attached(self):
        for o in self.options:
            assert o.lead_time_path is not None

    def test_material_days_less_than_total_days(self):
        for o in self.options:
            assert o.material_lead_time_days < o.total_lead_time_days

    def test_names_match_labels(self):
        opt_a = next(o for o in self.options if o.option_label == "A")
        opt_b = next(o for o in self.options if o.option_label == "B")
        opt_c = next(o for o in self.options if o.option_label == "C")
        assert "fastest" in opt_a.option_name.lower() or "fast" in opt_a.option_name.lower()
        assert "cost" in opt_b.option_name.lower() or "low" in opt_b.option_name.lower()
        assert "balanced" in opt_c.option_name.lower() or "recommended" in opt_c.option_name.lower()
