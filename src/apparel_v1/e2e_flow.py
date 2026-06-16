"""
Apparel & Textile v1.0 E2E Flow Orchestrator.

Runs the complete 14-step procurement flow from B-side buyer inquiry through
supplier responses, lead time calculation, option generation, QC process card,
human approval gate, buyer quote, and final decision packet output.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.apparel_v1.inquiry_intake import BuyerInquiry, intake_inquiry, CANONICAL_INQUIRY
from src.apparel_v1.requirement_extractor import ExtractedRequirements, extract_requirements
from src.apparel_v1.missing_info_checker import MissingInfoReport, check_missing_info
from src.apparel_v1.upstream_planner import UpstreamPlan, plan_upstream
from src.apparel_v1.supplier_response_simulator import MockSupplierResponse, simulate_supplier_responses
from src.apparel_v1.option_generator import BuyerOption, generate_options
from src.apparel_v1.quote_generator import (
    QCProcessCard,
    BuyerQuote,
    generate_qc_process_card,
    generate_buyer_quote,
)


@dataclass
class ExecutionEvent:
    event_id: str = field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    step: str = ""
    status: str = "ok"
    payload: dict = field(default_factory=dict)
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ApprovalGate:
    gate_id: str = field(default_factory=lambda: f"GATE-{uuid.uuid4().hex[:8].upper()}")
    gate_type: str = "merchandiser_approval"
    status: str = "pending"
    approved_by: str = ""
    approved_at: Optional[str] = None
    notes: str = ""


@dataclass
class E2EFlowResult:
    flow_id: str
    started_at: str
    completed_at: Optional[str] = None
    # Step outputs
    inquiry: Optional[BuyerInquiry] = None
    requirements: Optional[ExtractedRequirements] = None
    missing_info: Optional[MissingInfoReport] = None
    upstream_plan: Optional[UpstreamPlan] = None
    supplier_responses: list[MockSupplierResponse] = field(default_factory=list)
    options: list[BuyerOption] = field(default_factory=list)
    qc_process_card: Optional[QCProcessCard] = None
    approval_gate: Optional[ApprovalGate] = None
    buyer_quote: Optional[BuyerQuote] = None
    # Execution graph
    execution_log: list[ExecutionEvent] = field(default_factory=list)
    # Flow status
    status: str = "running"
    error: Optional[str] = None


def run_apparel_v1_e2e(
    raw_inquiry: str = CANONICAL_INQUIRY,
    auto_approve: bool = True,
    project_id: str = "",
) -> E2EFlowResult:
    """
    Run the Apparel & Textile v1.0 E2E procurement flow.

    Steps:
      1.  B-side inquiry intake
      2.  Requirement extraction (deterministic rule-based parser)
      3.  Missing information detection
      4.  M-side role context resolution
      5.  Upstream dependency planning
      6.  Upstream supplier inquiry generation
      7.  Mock supplier responses (3 profiles)
      8.  Lead time path calculation per supplier
      9.  Price / delivery option generation (A / B / C)
      10. QC standard and process card generation
      11. Human approval gate (auto_approve=True by default)
      12. Buyer-facing quote generation
      13. Execution graph record
      14. Decision packet output
    """
    if not project_id:
        project_id = f"PROJ-{uuid.uuid4().hex[:8].upper()}"

    result = E2EFlowResult(
        flow_id=f"FLOW-{uuid.uuid4().hex[:8].upper()}",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    def _log(step: str, status: str = "ok", **payload_kwargs: object) -> None:
        result.execution_log.append(
            ExecutionEvent(step=step, status=status, payload=dict(payload_kwargs))
        )

    try:
        # Step 1: Inquiry intake
        inquiry = intake_inquiry(raw_inquiry)
        result.inquiry = inquiry
        _log("inquiry_intake",
             inquiry_id=inquiry.inquiry_id,
             channel=inquiry.channel,
             text_length=len(inquiry.raw_text))

        # Step 2: Requirement extraction
        requirements = extract_requirements(inquiry)
        result.requirements = requirements
        _log("requirement_extraction",
             quantity=requirements.quantity,
             product_type=requirements.product_type,
             fabric_type=requirements.fabric_type,
             delivery_deadline_days=requirements.delivery_deadline_days,
             trade_term=requirements.trade_term)

        # Step 3: Missing information detection
        missing_info = check_missing_info(requirements)
        result.missing_info = missing_info
        _log("missing_info_check",
             is_complete=missing_info.is_complete,
             missing_count=len(missing_info.missing_fields),
             completeness_score=missing_info.completeness_score,
             missing_fields=missing_info.missing_fields)

        if not missing_info.is_complete:
            _log("missing_info_warning",
                 status="warning",
                 missing_fields=missing_info.missing_fields,
                 clarification_questions=missing_info.clarification_questions)

        # Steps 4–6: M-side role resolution, upstream planning, supplier inquiry generation
        upstream_plan = plan_upstream(requirements)
        result.upstream_plan = upstream_plan
        _log("upstream_planning",
             m_roles=[r.role for r in upstream_plan.m_roles],
             dependency_count=len(upstream_plan.dependencies),
             supplier_inquiry_count=len(upstream_plan.supplier_inquiries),
             estimated_upstream_days=upstream_plan.total_upstream_days_estimate)

        # Step 7: Mock supplier responses
        supplier_responses = simulate_supplier_responses(requirements)
        result.supplier_responses = supplier_responses
        _log("supplier_responses",
             supplier_count=len(supplier_responses),
             suppliers=[r.supplier_name for r in supplier_responses],
             profiles=[r.profile for r in supplier_responses])

        # Steps 8–9: Lead time calculation + option generation
        buyer_deadline = requirements.delivery_deadline_days or 45
        options = generate_options(
            supplier_responses=supplier_responses,
            quantity=requirements.quantity or 10000,
            buyer_deadline_days=buyer_deadline,
            project_id=project_id,
        )
        result.options = options
        _log("option_generation",
             option_count=len(options),
             options=[{
                 "label": o.option_label,
                 "name": o.option_name,
                 "total_lead_time_days": o.total_lead_time_days,
                 "total_price_usd": o.total_price_usd,
                 "feasible": o.feasible_for_deadline,
                 "slack_days": o.slack_days,
             } for o in options])

        # Step 10: QC process card generation
        qc_card = generate_qc_process_card(requirements)
        result.qc_process_card = qc_card
        _log("qc_process_card",
             card_id=qc_card.card_id,
             standard=qc_card.qc_standard,
             milestone_count=len(qc_card.inspection_milestones),
             target_market_notes=qc_card.target_market_notes)

        # Step 11: Human approval gate
        gate = ApprovalGate(gate_type="merchandiser_approval")
        if auto_approve:
            gate.status = "approved"
            gate.approved_by = "SYSTEM-AUTO"
            gate.approved_at = datetime.now(timezone.utc).isoformat()
            gate.notes = "Auto-approved — E2E flow, human gate bypassed"
        result.approval_gate = gate
        _log("approval_gate",
             gate_id=gate.gate_id,
             gate_status=gate.status,
             auto_approve=auto_approve,
             approved_by=gate.approved_by or None)

        # Step 12: Buyer quote generation
        buyer_quote = generate_buyer_quote(
            requirements=requirements,
            options=options,
            qc_process_card=qc_card,
            human_approved=(gate.status == "approved"),
        )
        result.buyer_quote = buyer_quote
        _log("buyer_quote_generated",
             quote_id=buyer_quote.quote_id,
             recommended_option=buyer_quote.recommended_option,
             human_approval_status=buyer_quote.human_approval_status,
             option_count=len(buyer_quote.options),
             validity_days=buyer_quote.validity_days)

        # Steps 13–14: Execution graph + decision packet summary
        _log("flow_complete",
             flow_id=result.flow_id,
             quote_id=buyer_quote.quote_id,
             recommended_option=buyer_quote.recommended_option,
             approval_status=gate.status,
             options_summary=[{
                 "label": o.option_label,
                 "name": o.option_name,
                 "total_lead_time_days": o.total_lead_time_days,
                 "unit_price_usd": o.unit_price_usd,
                 "total_price_usd": o.total_price_usd,
                 "feasible_for_deadline": o.feasible_for_deadline,
                 "risk_flag_count": len(o.risk_flags),
             } for o in options])

        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.status = "completed"

    except Exception as exc:
        result.status = "failed"
        result.error = str(exc)
        _log("error", status="error", error=str(exc), error_type=type(exc).__name__)
        raise

    return result


def format_decision_packet(result: E2EFlowResult) -> dict:
    """
    Format the E2E flow result as a structured decision packet.
    This is the canonical output document for the buyer and internal records.
    """
    if not result.buyer_quote:
        return {
            "status": result.status,
            "error": result.error,
            "flow_id": result.flow_id,
        }

    quote = result.buyer_quote
    packet: dict = {
        "flow_id": result.flow_id,
        "inquiry_id": result.inquiry.inquiry_id if result.inquiry else None,
        "quote_id": quote.quote_id,
        "generated_at": quote.generated_at,
        "product_summary": quote.product_summary,
        "recommended_option": quote.recommended_option,
        "human_approval_status": quote.human_approval_status,
        "completeness_score": (
            result.missing_info.completeness_score if result.missing_info else None
        ),
        "options": [],
        "qc_summary": None,
        "execution_steps": len(result.execution_log),
        "missing_fields": (
            result.missing_info.missing_fields if result.missing_info else []
        ),
        "status": result.status,
    }

    for opt in quote.options:
        packet["options"].append({
            "label": opt.option_label,
            "name": opt.option_name,
            "supplier": opt.supplier_name,
            "location": opt.supplier_location,
            "quantity": opt.quantity,
            "unit_price_usd": opt.unit_price_usd,
            "total_price_usd": opt.total_price_usd,
            "currency": opt.currency,
            "material_lead_time_days": opt.material_lead_time_days,
            "production_lead_time_days": opt.production_lead_time_days,
            "total_lead_time_days": opt.total_lead_time_days,
            "feasible_for_deadline": opt.feasible_for_deadline,
            "slack_days": opt.slack_days,
            "risk_flags": opt.risk_flags,
            "qc_milestones": [m["milestone"] for m in opt.qc_milestone_plan],
            "supplier_dependency_summary": opt.supplier_dependency_summary,
            "evidence_references": opt.evidence_references[:5],
            "human_approval_status": opt.human_approval_status,
        })

    if result.qc_process_card:
        card = result.qc_process_card
        packet["qc_summary"] = {
            "card_id": card.card_id,
            "product_type": card.product_type,
            "standard": card.qc_standard,
            "inspection_stages": len(card.inspection_milestones),
            "critical_defect_categories": len(card.critical_defects),
            "major_defect_categories": len(card.major_defects),
            "acceptance_criteria_count": len(card.acceptance_criteria),
            "target_market_notes": card.target_market_notes,
        }

    return packet
