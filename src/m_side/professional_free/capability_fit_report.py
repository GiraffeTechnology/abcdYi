"""
Capability Fit Report — human-readable summary of CAD-to-CNC matching result.
"""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.m_side.professional_free.cad_cnc_matcher import CADCNCMachiningMatchResult
from src.m_side.m_event_logger import log_m_event


class CapabilityFitReport(BaseModel):
    report_id: str
    project_id: str
    actor_id: str
    buyer_facing_summary_en: str
    buyer_facing_summary_zh: str
    internal_summary: str
    can_quote_now: bool
    can_make_in_house: bool
    recommended_next_actions: list[str] = Field(default_factory=list)
    required_upstream_inquiries: list[str] = Field(default_factory=list)
    required_subcontractor_inquiries: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def generate_capability_fit_report(match: CADCNCMachiningMatchResult) -> CapabilityFitReport:
    """
    Generate a human-readable capability fit report from a CAD-CNC match result.
    """
    next_actions: list[str] = []
    buyer_lines_en: list[str] = []
    buyer_lines_zh: list[str] = []

    # Work envelope
    if match.work_envelope_fit == "fit":
        buyer_lines_en.append("Work envelope: the part dimensions fit within our machining center.")
        buyer_lines_zh.append("加工空间：零件尺寸在我们的加工中心范围内。")
    elif match.work_envelope_fit == "not_fit":
        buyer_lines_en.append("Work envelope: the part exceeds our machine envelope — subcontractor required.")
        buyer_lines_zh.append("加工空间：零件超出加工范围，需要外协加工。")
        next_actions.append("Identify subcontractor for large-part machining")
    else:
        buyer_lines_en.append("Work envelope: dimensions not confirmed — please provide part dimensions.")
        buyer_lines_zh.append("加工空间：尺寸未确认，请提供零件尺寸。")

    # Material
    if match.material_fit == "in_stock":
        buyer_lines_en.append("Material: available in stock.")
        buyer_lines_zh.append("材料：库存充足。")
    elif match.material_fit == "purchasable":
        buyer_lines_en.append("Material: not in stock — material supplier confirmation required.")
        buyer_lines_zh.append("材料：无现货，需确认供应商供货。")
        next_actions.append("Ask material suppliers for availability and lead time")
    elif match.material_fit == "not_supported":
        buyer_lines_en.append("Material: not supported by current shop equipment — alternative required.")
        buyer_lines_zh.append("材料：当前设备不支持该材料，需替代方案。")
        next_actions.append("Identify alternative material supplier or subcontractor")
    else:
        buyer_lines_en.append("Material: type not confirmed — please specify material.")
        buyer_lines_zh.append("材料：未指定，请确认材料类型。")

    # Tolerance
    if match.tolerance_fit == "fit":
        buyer_lines_en.append("Tolerance: within our standard machining capability.")
        buyer_lines_zh.append("精度：在我们的标准加工能力范围内。")
    elif match.tolerance_fit == "marginal":
        buyer_lines_en.append("Tolerance: marginal — QC review required before final lead-time commitment.")
        buyer_lines_zh.append("精度：接近极限，需QC确认后再承诺交期。")
        next_actions.append("Schedule QC review for tolerance validation")
    elif match.tolerance_fit == "not_fit":
        buyer_lines_en.append("Tolerance: beyond our capability — precision subcontractor required.")
        buyer_lines_zh.append("精度：超出我们的能力，需精密加工外协。")
        next_actions.append("Identify precision machining subcontractor")

    # Surface finish
    if match.surface_finish_fit == "fit":
        buyer_lines_en.append("Surface finish: achievable in-house.")
        buyer_lines_zh.append("表面处理：可在内部完成。")
    elif match.surface_finish_fit == "requires_external_process":
        buyer_lines_en.append("Surface finish: requires external surface treatment process.")
        buyer_lines_zh.append("表面处理：需外协表面处理工序。")
        next_actions.append("Ask surface treatment subcontractor")

    # QC
    if match.qc_fit == "fit":
        buyer_lines_en.append("QC: inspection available in-house.")
        buyer_lines_zh.append("质检：可在内部进行检验。")
    elif match.qc_fit == "external_qc_required":
        buyer_lines_en.append("QC: external QC provider required.")
        buyer_lines_zh.append("质检：需外部质检机构。")
        next_actions.append("Ask QC provider for inspection service")
    elif match.qc_fit == "missing":
        buyer_lines_en.append("QC: no QC capability registered — external QC required.")
        buyer_lines_zh.append("质检：未登记质检设备，需外部质检。")
        next_actions.append("Ask QC provider for inspection service")

    # Schedule
    if match.schedule_fit == "fit":
        buyer_lines_en.append("Schedule: capacity available.")
        buyer_lines_zh.append("排期：产能充足。")
    elif match.schedule_fit == "limited":
        buyer_lines_en.append("Schedule: limited capacity — subcontractor backup recommended.")
        buyer_lines_zh.append("排期：产能有限，建议联系备用外协。")
        next_actions.append("Contact backup subcontractor for capacity")
    elif match.schedule_fit == "not_fit":
        buyer_lines_en.append("Schedule: fully booked — subcontracting required.")
        buyer_lines_zh.append("排期：已满负荷，需外协生产。")

    buyer_summary_en = (
        "CAD-to-CNC Matching Result:\n" +
        "\n".join(f"  - {l}" for l in buyer_lines_en) +
        f"\n\nOverall machine fit score: {match.machine_fit_score:.0%}. "
        f"{'We can quote this part based on current capability' if match.can_make_in_house else 'Upstream confirmations required before final quote'}. "
        f"See recommended actions below."
    )

    buyer_summary_zh = (
        "CAD与CNC能力匹配结果：\n" +
        "\n".join(f"  - {l}" for l in buyer_lines_zh) +
        f"\n\n综合匹配分数：{match.machine_fit_score:.0%}。"
        f"{'可基于当前能力报价' if match.can_make_in_house else '需完成上游确认后再报最终价'}。"
    )

    internal = (
        f"Match ID: {match.match_id}\n"
        f"can_make_in_house={match.can_make_in_house}, machine_fit_score={match.machine_fit_score}\n"
        f"upstream_deps={match.required_upstream_dependencies}\n"
        f"subcontract_deps={match.required_subcontract_dependencies}\n"
        f"risk_flags={match.risk_flags}\n"
        f"\nExplanation:\n{match.explanation}"
    )

    can_quote_now = (
        match.can_make_in_house
        and not match.required_upstream_dependencies
        and not match.required_subcontract_dependencies
        and match.confidence_score >= 0.5
    )

    report = CapabilityFitReport(
        report_id=f"FITREPORT-{uuid.uuid4().hex[:8].upper()}",
        project_id=match.project_id,
        actor_id=match.actor_id,
        buyer_facing_summary_en=buyer_summary_en,
        buyer_facing_summary_zh=buyer_summary_zh,
        internal_summary=internal,
        can_quote_now=can_quote_now,
        can_make_in_house=match.can_make_in_house,
        recommended_next_actions=list(dict.fromkeys(next_actions)),
        required_upstream_inquiries=match.required_upstream_dependencies,
        required_subcontractor_inquiries=match.required_subcontract_dependencies,
        risk_flags=match.risk_flags,
        confidence_score=match.confidence_score,
    )

    log_m_event(
        event_type="CAPABILITY_FIT_REPORT_CREATED",
        b_workspace_id=match.project_id,
        supplier_id=match.actor_id,
        payload={
            "report_id": report.report_id,
            "can_quote_now": can_quote_now,
            "can_make_in_house": match.can_make_in_house,
            "confidence_score": match.confidence_score,
            "next_actions": next_actions,
        },
    )

    return report
