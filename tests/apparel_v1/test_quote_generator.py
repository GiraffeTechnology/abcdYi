"""Unit tests for QC process card and buyer quote generation."""
import pytest
from src.apparel_v1.inquiry_intake import intake_inquiry, CANONICAL_INQUIRY
from src.apparel_v1.requirement_extractor import extract_requirements
from src.apparel_v1.supplier_response_simulator import simulate_supplier_responses
from src.apparel_v1.option_generator import generate_options
from src.apparel_v1.quote_generator import (
    generate_qc_process_card,
    generate_buyer_quote,
    QCProcessCard,
    BuyerQuote,
)


class TestGenerateQCProcessCard:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        self.card = generate_qc_process_card(self.req)

    def test_returns_qc_process_card(self):
        assert isinstance(self.card, QCProcessCard)

    def test_card_id_assigned(self):
        assert self.card.card_id.startswith("QC-CARD-")

    def test_standard_is_aql_25(self):
        assert self.card.qc_standard == "AQL 2.5"

    def test_has_at_least_five_milestones(self):
        assert len(self.card.inspection_milestones) >= 5

    def test_milestone_has_required_keys(self):
        for ms in self.card.inspection_milestones:
            assert "stage" in ms
            assert "timing" in ms
            assert "check_points" in ms
            assert "pass_criteria" in ms

    def test_has_acceptance_criteria(self):
        assert len(self.card.acceptance_criteria) > 0

    def test_has_critical_defects(self):
        assert len(self.card.critical_defects) > 0

    def test_has_major_defects(self):
        assert len(self.card.major_defects) > 0

    def test_has_minor_defects(self):
        assert len(self.card.minor_defects) > 0

    def test_japan_notes_present_for_japan_market(self):
        assert "Japan" in self.card.target_market_notes

    def test_japan_specific_acceptance_criteria(self):
        # Japan-specific criteria should be added for Japan market orders
        japan_criteria = [c for c in self.card.acceptance_criteria if "japan" in c.lower() or "Japan" in c]
        assert len(japan_criteria) > 0


class TestGenerateBuyerQuote:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        responses = simulate_supplier_responses(self.req)
        self.options = generate_options(
            supplier_responses=responses,
            quantity=10000,
            buyer_deadline_days=45,
        )
        self.qc_card = generate_qc_process_card(self.req)
        self.quote = generate_buyer_quote(
            requirements=self.req,
            options=self.options,
            qc_process_card=self.qc_card,
            human_approved=True,
        )

    def test_returns_buyer_quote(self):
        assert isinstance(self.quote, BuyerQuote)

    def test_quote_id_assigned(self):
        assert self.quote.quote_id.startswith("QUOTE-")

    def test_inquiry_id_linked(self):
        assert self.quote.inquiry_id == self.req.inquiry_id

    def test_generated_at_set(self):
        assert self.quote.generated_at is not None
        assert "T" in self.quote.generated_at

    def test_product_summary_populated(self):
        assert self.quote.product_summary
        assert "10,000" in self.quote.product_summary or "10000" in self.quote.product_summary

    def test_has_three_options(self):
        assert len(self.quote.options) == 3

    def test_recommended_option_is_c(self):
        assert self.quote.recommended_option == "C"

    def test_qc_process_card_attached(self):
        assert self.quote.qc_process_card is not None
        assert self.quote.qc_process_card.qc_standard == "AQL 2.5"

    def test_human_approved_sets_status(self):
        assert self.quote.human_approval_status == "approved"

    def test_options_get_approved_status(self):
        for opt in self.quote.options:
            assert opt.human_approval_status == "approved"

    def test_pending_when_not_approved(self):
        quote = generate_buyer_quote(
            requirements=self.req,
            options=self.options,
            qc_process_card=self.qc_card,
            human_approved=False,
        )
        assert quote.human_approval_status == "pending"

    def test_validity_days_set(self):
        assert self.quote.validity_days == 7

    def test_notes_non_empty(self):
        assert self.quote.notes
        assert "FOB" in self.quote.notes or "USD" in self.quote.notes
