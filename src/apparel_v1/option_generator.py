"""
Option generator for the apparel v1 E2E flow.
Calculates lead time paths for each supplier response and produces
3 structured buyer-facing options: A (fastest), B (lowest cost), C (balanced).
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.apparel_v1.supplier_response_simulator import MockSupplierResponse
from src.lead_time.lead_time_calculator import calculate_lead_time_path
from src.lead_time.models import LeadTimePath, ProductionCapacity


# Profile → option label mapping
_PROFILE_LABEL = {
    "fast": "A",
    "cheap": "B",
    "balanced": "C",
}

_LABEL_NAME = {
    "A": "Fastest Delivery",
    "B": "Lowest Cost",
    "C": "Balanced / Recommended",
}


@dataclass
class BuyerOption:
    option_label: str           # "A", "B", or "C"
    option_name: str            # "Fastest Delivery" etc.
    supplier_id: str
    supplier_name: str
    supplier_location: str
    quantity: int
    unit_price_usd: float
    total_price_usd: float
    currency: str
    # Lead time breakdown
    material_lead_time_days: int
    production_lead_time_days: int
    total_lead_time_days: int
    feasible_for_deadline: bool
    slack_days: Optional[int]
    # QC
    qc_milestone_plan: list[dict] = field(default_factory=list)
    # Risk
    risk_flags: list[str] = field(default_factory=list)
    # Supplier dependency summary
    supplier_dependency_summary: str = ""
    # Evidence
    evidence_references: list[str] = field(default_factory=list)
    # Approval
    human_approval_status: str = "pending"
    # Internal reference
    lead_time_path: Optional[LeadTimePath] = field(default=None, repr=False)
    response_id: str = ""


def generate_options(
    supplier_responses: list[MockSupplierResponse],
    quantity: int,
    buyer_deadline_days: int,
    project_id: str = "",
) -> list[BuyerOption]:
    """
    Generate buyer-facing A/B/C options from a list of supplier responses.
    Each response is mapped to an option label by its profile.
    Returns options sorted by label (A, B, C).
    """
    if not project_id:
        project_id = f"PROJ-{uuid.uuid4().hex[:8].upper()}"

    options: list[BuyerOption] = []

    for resp in supplier_responses:
        label = _PROFILE_LABEL.get(resp.profile, "C")
        name = _LABEL_NAME.get(label, "Option")

        cap = ProductionCapacity(
            actor_id=resp.supplier_id,
            daily_capacity_units=float(max(1, resp.daily_capacity_pcs)),
            setup_days=1.0,
            queue_days=0.0,
            confidence_score=resp.confidence_score,
        )

        path = calculate_lead_time_path(
            supplier_response_id=resp.response_id,
            supplier_id=resp.supplier_id,
            supplier_name=resp.supplier_name,
            project_id=project_id,
            quantity=quantity,
            fabric_days=resp.fabric_days or None,
            trim_days=resp.trim_days or None,
            qc_days=resp.qc_days or None,
            packaging_days=resp.packaging_days or None,
            logistics_days=resp.logistics_days or None,
            production_capacity=cap,
            supplier_stated_total_days=resp.supplier_stated_total_days or None,
            risk_flags=list(resp.risk_flags),
            missing_fields=list(resp.missing_fields),
            confidence_score=resp.confidence_score,
            completeness_score=resp.completeness_score,
            unit_price=resp.unit_price_usd,
            total_price=resp.total_price_usd,
            currency=resp.currency,
            buyer_deadline_days=buyer_deadline_days,
        )

        qc_milestones = _build_qc_milestones(path, resp)
        dep_summary = _build_dependency_summary(path, resp)

        options.append(BuyerOption(
            option_label=label,
            option_name=name,
            supplier_id=resp.supplier_id,
            supplier_name=resp.supplier_name,
            supplier_location=resp.location,
            quantity=quantity,
            unit_price_usd=resp.unit_price_usd,
            total_price_usd=resp.total_price_usd,
            currency=resp.currency,
            material_lead_time_days=int(path.material_ready_days),
            production_lead_time_days=int(path.production_days),
            total_lead_time_days=path.total_lead_time_days,
            feasible_for_deadline=path.feasible_before_deadline,
            slack_days=path.slack_days,
            qc_milestone_plan=qc_milestones,
            risk_flags=path.risk_flags,
            supplier_dependency_summary=dep_summary,
            evidence_references=path.evidence_refs,
            human_approval_status="pending",
            lead_time_path=path,
            response_id=resp.response_id,
        ))

    options.sort(key=lambda o: o.option_label)
    return options


def _build_qc_milestones(path: LeadTimePath, resp: MockSupplierResponse) -> list[dict]:
    """Build QC milestone plan from lead time path and supplier response."""
    mat_d = int(path.material_ready_days)
    prod_start = mat_d
    prod_end = int(path.material_ready_days + path.production_days)
    inline_day = prod_start + max(1, int(resp.production_days * 0.55))

    return [
        {
            "milestone": "Fabric Inspection",
            "day": f"D+{mat_d}",
            "responsible": "QC Inspector + Factory",
            "standard": "4-point fabric inspection — defects per 100m²",
        },
        {
            "milestone": "Cutting Check",
            "day": f"D+{mat_d + 2}",
            "responsible": "Factory QC",
            "standard": "Size accuracy ±0.3cm, marker efficiency check",
        },
        {
            "milestone": "Inline Inspection (50% production)",
            "day": f"D+{inline_day}",
            "responsible": "Third-party QC Inspector",
            "standard": "AQL 2.5 — workmanship, stitching, trims",
        },
        {
            "milestone": "Final QC Inspection",
            "day": f"D+{prod_end}",
            "responsible": "Third-party QC Inspector",
            "standard": "AQL 2.5 Level II — full visual, measurement, packing",
        },
        {
            "milestone": "Pre-Shipment Inspection",
            "day": f"D+{prod_end + 2}",
            "responsible": "Buyer Representative or Third-party",
            "standard": "100% carton count, label & barcode compliance",
        },
    ]


def _build_dependency_summary(path: LeadTimePath, resp: MockSupplierResponse) -> str:
    """Build a one-line supplier dependency summary from path data."""
    mat_d = int(path.material_ready_days)
    prod_end = int(path.material_ready_days + path.production_days)
    qc_end = prod_end + (resp.qc_days or 2)
    return (
        f"{resp.supplier_name} ({resp.location}): "
        f"fabric/trim ready D+{mat_d}, "
        f"production D+{mat_d}–D+{prod_end}, "
        f"QC D+{prod_end}–D+{qc_end}, "
        f"FOB D+{path.total_lead_time_days}"
    )
