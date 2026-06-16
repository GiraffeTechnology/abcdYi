"""
E2E tests for the Apparel & Textile v1.0 full procurement flow.
All tests are deterministic and run without live DB or LLM API calls.
"""
import pytest
from src.apparel_v1.e2e_flow import run_apparel_v1_e2e, format_decision_packet, E2EFlowResult
from src.apparel_v1.inquiry_intake import CANONICAL_INQUIRY


EXPECTED_STEPS = [
    "inquiry_intake",
    "requirement_extraction",
    "missing_info_check",
    "upstream_planning",
    "supplier_responses",
    "option_generation",
    "qc_process_card",
    "approval_gate",
    "buyer_quote_generated",
    "flow_complete",
]


class TestE2EFlowCompletion:
    def test_canonical_inquiry_completes(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        assert result.status == "completed"
        assert result.error is None

    def test_result_has_flow_id(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        assert result.flow_id.startswith("FLOW-")

    def test_timestamps_set(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        assert result.started_at is not None
        assert result.completed_at is not None

    def test_custom_inquiry_completes(self):
        custom = "Need 5000 polyester jackets, navy blue, size M-XXL, delivery in 60 days, CIF Shanghai."
        result = run_apparel_v1_e2e(custom, auto_approve=True)
        assert result.status == "completed"

    def test_custom_project_id_used(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, project_id="PROJ-TEST-001")
        path = result.options[0].lead_time_path
        assert path.project_id == "PROJ-TEST-001"


class TestE2EOptions:
    def setup_method(self):
        self.result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)

    def test_produces_three_options(self):
        assert len(self.result.options) == 3

    def test_option_labels_are_a_b_c(self):
        labels = {o.option_label for o in self.result.options}
        assert labels == {"A", "B", "C"}

    def test_option_a_is_fastest(self):
        opt_a = next(o for o in self.result.options if o.option_label == "A")
        opt_b = next(o for o in self.result.options if o.option_label == "B")
        assert opt_a.total_lead_time_days < opt_b.total_lead_time_days

    def test_option_b_is_cheapest(self):
        opt_a = next(o for o in self.result.options if o.option_label == "A")
        opt_b = next(o for o in self.result.options if o.option_label == "B")
        assert opt_b.total_price_usd < opt_a.total_price_usd

    def test_option_c_is_recommended(self):
        assert self.result.buyer_quote.recommended_option == "C"

    def test_each_option_has_quantity(self):
        for opt in self.result.options:
            assert opt.quantity == 10000

    def test_each_option_has_prices(self):
        for opt in self.result.options:
            assert opt.unit_price_usd > 0
            assert opt.total_price_usd > 0

    def test_each_option_has_lead_times(self):
        for opt in self.result.options:
            assert opt.total_lead_time_days > 0
            assert opt.production_lead_time_days > 0
            assert opt.material_lead_time_days >= 0

    def test_each_option_has_qc_milestones(self):
        for opt in self.result.options:
            assert len(opt.qc_milestone_plan) >= 4

    def test_each_option_has_risk_info(self):
        for opt in self.result.options:
            assert isinstance(opt.risk_flags, list)

    def test_each_option_has_dependency_summary(self):
        for opt in self.result.options:
            assert opt.supplier_dependency_summary
            assert len(opt.supplier_dependency_summary) > 10

    def test_each_option_has_evidence_refs(self):
        for opt in self.result.options:
            assert len(opt.evidence_references) > 0

    def test_option_a_feasible_for_45d_deadline(self):
        opt_a = next(o for o in self.result.options if o.option_label == "A")
        assert opt_a.feasible_for_deadline is True


class TestE2EApprovalGate:
    def test_auto_approve_true_sets_approved(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        assert result.approval_gate.status == "approved"
        assert result.buyer_quote.human_approval_status == "approved"

    def test_auto_approve_false_leaves_pending(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=False)
        assert result.approval_gate.status == "pending"
        assert result.buyer_quote.human_approval_status == "pending"

    def test_approved_options_have_approved_status(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        for opt in result.options:
            assert opt.human_approval_status == "approved"

    def test_pending_options_have_pending_status(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=False)
        for opt in result.options:
            assert opt.human_approval_status == "pending"

    def test_gate_has_approved_by_when_auto(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        assert result.approval_gate.approved_by == "SYSTEM-AUTO"
        assert result.approval_gate.approved_at is not None

    def test_gate_id_assigned(self):
        result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        assert result.approval_gate.gate_id.startswith("GATE-")


class TestE2EExecutionLog:
    def setup_method(self):
        self.result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)

    def test_all_expected_steps_logged(self):
        logged_steps = [e.step for e in self.result.execution_log]
        for step in EXPECTED_STEPS:
            assert step in logged_steps, f"Step '{step}' missing from execution log"

    def test_all_log_events_have_event_id(self):
        for evt in self.result.execution_log:
            assert evt.event_id.startswith("EVT-")

    def test_all_log_events_have_timestamps(self):
        for evt in self.result.execution_log:
            assert evt.occurred_at is not None

    def test_no_error_events_on_success(self):
        error_events = [e for e in self.result.execution_log if e.status == "error"]
        assert len(error_events) == 0

    def test_log_is_ordered_by_flow(self):
        steps = [e.step for e in self.result.execution_log]
        # inquiry_intake should come before flow_complete
        assert steps.index("inquiry_intake") < steps.index("flow_complete")


class TestE2ERequirements:
    def setup_method(self):
        self.result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)

    def test_quantity_extracted_correctly(self):
        assert self.result.requirements.quantity == 10000

    def test_deadline_extracted_correctly(self):
        assert self.result.requirements.delivery_deadline_days == 45

    def test_trade_term_extracted(self):
        assert self.result.requirements.trade_term == "FOB"

    def test_fabric_type_extracted(self):
        assert "cotton" in self.result.requirements.fabric_type.lower()

    def test_size_range_extracted(self):
        assert self.result.requirements.size_range == "S/M/L/XL"

    def test_target_market_extracted(self):
        assert self.result.requirements.target_market == "Japan"


class TestE2EQCProcessCard:
    def setup_method(self):
        self.result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)

    def test_qc_card_generated(self):
        assert self.result.qc_process_card is not None

    def test_qc_standard_is_aql_25(self):
        assert self.result.qc_process_card.qc_standard == "AQL 2.5"

    def test_has_inspection_milestones(self):
        assert len(self.result.qc_process_card.inspection_milestones) >= 5

    def test_has_defect_categories(self):
        card = self.result.qc_process_card
        assert len(card.critical_defects) > 0
        assert len(card.major_defects) > 0
        assert len(card.minor_defects) > 0

    def test_japan_market_notes_present(self):
        assert "Japan" in self.result.qc_process_card.target_market_notes


class TestE2EDecisionPacket:
    def setup_method(self):
        self.result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)
        self.packet = format_decision_packet(self.result)

    def test_packet_is_dict(self):
        assert isinstance(self.packet, dict)

    def test_packet_has_flow_id(self):
        assert "flow_id" in self.packet
        assert self.packet["flow_id"].startswith("FLOW-")

    def test_packet_has_quote_id(self):
        assert "quote_id" in self.packet
        assert self.packet["quote_id"].startswith("QUOTE-")

    def test_packet_has_three_options(self):
        assert len(self.packet["options"]) == 3

    def test_packet_options_have_required_fields(self):
        required = [
            "label", "name", "supplier", "location", "quantity",
            "unit_price_usd", "total_price_usd", "currency",
            "material_lead_time_days", "production_lead_time_days",
            "total_lead_time_days", "feasible_for_deadline",
            "risk_flags", "qc_milestones", "supplier_dependency_summary",
            "evidence_references", "human_approval_status",
        ]
        for opt in self.packet["options"]:
            for field in required:
                assert field in opt, f"Missing field '{field}' in packet option"

    def test_packet_has_qc_summary(self):
        assert "qc_summary" in self.packet
        assert self.packet["qc_summary"] is not None
        assert self.packet["qc_summary"]["standard"] == "AQL 2.5"

    def test_packet_recommended_option_is_c(self):
        assert self.packet["recommended_option"] == "C"

    def test_packet_approval_status_approved(self):
        assert self.packet["human_approval_status"] == "approved"

    def test_packet_completeness_score(self):
        assert self.packet["completeness_score"] is not None
        assert 0.0 <= self.packet["completeness_score"] <= 1.0

    def test_packet_execution_steps_count(self):
        assert self.packet["execution_steps"] >= len(EXPECTED_STEPS)

    def test_packet_status_completed(self):
        assert self.packet["status"] == "completed"


class TestE2EUpstreamPlan:
    def setup_method(self):
        self.result = run_apparel_v1_e2e(CANONICAL_INQUIRY, auto_approve=True)

    def test_upstream_plan_present(self):
        assert self.result.upstream_plan is not None

    def test_m_roles_include_merchandiser(self):
        roles = [r.role for r in self.result.upstream_plan.m_roles]
        assert "merchandiser" in roles

    def test_m_roles_include_factory(self):
        roles = [r.role for r in self.result.upstream_plan.m_roles]
        assert "garment_factory" in roles

    def test_supplier_inquiries_generated(self):
        assert len(self.result.upstream_plan.supplier_inquiries) >= 2

    def test_supplier_responses_present(self):
        assert len(self.result.supplier_responses) == 3
