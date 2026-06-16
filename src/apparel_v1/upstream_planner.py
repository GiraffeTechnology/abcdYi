"""
Upstream dependency planner and supplier inquiry generator for the apparel v1 E2E flow.
Resolves M-side role context and plans the full upstream procurement chain.
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.apparel_v1.requirement_extractor import ExtractedRequirements


@dataclass
class MRoleContext:
    role: str
    actor_id: str
    actor_name: str
    responsibilities: list[str] = field(default_factory=list)
    location: str = "China"


@dataclass
class UpstreamDependency:
    dependency_id: str
    dependency_type: str
    description: str
    required_by_day: int
    estimated_lead_days: int
    supplier_actor: Optional[str] = None
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class UpstreamPlan:
    plan_id: str
    inquiry_id: str
    m_roles: list[MRoleContext] = field(default_factory=list)
    dependencies: list[UpstreamDependency] = field(default_factory=list)
    supplier_inquiries: list[dict] = field(default_factory=list)
    total_upstream_days_estimate: int = 0


def resolve_m_side_roles(requirements: ExtractedRequirements) -> list[MRoleContext]:
    """
    Resolve which M-side roles are needed based on the order requirements.
    Always includes: merchandiser, garment_factory.
    Conditionally adds: fabric_sourcer, qc_inspector, logistics_coordinator.
    """
    roles: list[MRoleContext] = []

    # Merchandiser is always the primary coordinator
    roles.append(MRoleContext(
        role="merchandiser",
        actor_id="MERCH-001",
        actor_name="Senior Merchandiser",
        responsibilities=[
            "Coordinate fabric sourcing and upstream suppliers",
            "Manage production schedule and milestone tracking",
            "Liaise with QC team and issue process card",
            "Generate and present buyer-facing quotation",
        ],
    ))

    # Fabric sourcer — needed when a specific fabric type is required
    if requirements.fabric_type:
        roles.append(MRoleContext(
            role="fabric_sourcer",
            actor_id="FAB-001",
            actor_name="Fabric Sourcing Agent",
            responsibilities=[
                f"Source {requirements.fabric_type} fabric matching spec",
                "Confirm GSM, width, and color availability",
                "Negotiate MOQ and delivery lead time",
                "Arrange fabric inspection before cutting",
            ],
        ))

    # Garment factory — always needed
    roles.append(MRoleContext(
        role="garment_factory",
        actor_id="FAC-001",
        actor_name="Garment Production Manager",
        responsibilities=[
            "Confirm production capacity and start date",
            "Issue production schedule with milestone dates",
            "Manage cutting, sewing, finishing, and packing",
            "Coordinate inline QC access",
        ],
    ))

    # QC inspector — always needed for commercial orders
    roles.append(MRoleContext(
        role="qc_inspector",
        actor_id="QC-001",
        actor_name="QC Inspector",
        responsibilities=[
            "Execute fabric inspection before cutting",
            "Perform inline inspection at 50% production",
            f"Execute final QC per {requirements.qc_standard or 'AQL 2.5'}",
            "Issue QC inspection report to buyer",
        ],
    ))

    # Logistics coordinator — needed for export FOB/CIF/CFR orders
    is_export = (
        requirements.trade_term in ("FOB", "CIF", "CFR")
        or (requirements.special_notes and "export" in requirements.special_notes.lower())
    )
    if is_export:
        roles.append(MRoleContext(
            role="logistics_coordinator",
            actor_id="LOG-001",
            actor_name="Export Logistics Coordinator",
            responsibilities=[
                f"Book {requirements.trade_term or 'FOB'} shipment to {requirements.destination or 'buyer port'}",
                "Arrange export customs clearance and documentation",
                "Coordinate container stuffing and loading",
                "Issue packing list, commercial invoice, and B/L",
            ],
        ))

    return roles


def plan_upstream_dependencies(requirements: ExtractedRequirements) -> list[UpstreamDependency]:
    """
    Plan upstream procurement dependencies in chronological order.
    Parallel dependencies (fabric + trim + packaging material) start on Day 0.
    Sequential dependencies (production -> QC -> logistics) follow in order.
    """
    deadline = requirements.delivery_deadline_days or 45
    qty = requirements.quantity or 10000
    deps: list[UpstreamDependency] = []

    # --- Parallel upstream phase ---
    fabric_lead = 10 if qty > 5000 else 7
    fabric_risk: list[str] = []
    if fabric_lead > deadline * 0.3:
        fabric_risk.append("fabric_lead_time_tight_vs_deadline")

    deps.append(UpstreamDependency(
        dependency_id=f"DEP-{uuid.uuid4().hex[:6].upper()}",
        dependency_type="fabric",
        description=f"Source and procure {requirements.fabric_type or 'fabric'} for {qty:,} pcs",
        required_by_day=fabric_lead,
        estimated_lead_days=fabric_lead,
        supplier_actor="FAB-001",
        risk_flags=fabric_risk,
    ))

    trim_lead = 5
    deps.append(UpstreamDependency(
        dependency_id=f"DEP-{uuid.uuid4().hex[:6].upper()}",
        dependency_type="trim",
        description="Source buttons, thread, interlining, care labels, and packaging materials",
        required_by_day=trim_lead,
        estimated_lead_days=trim_lead,
        supplier_actor="FAC-001",
    ))

    # --- Sequential phase starts after upstream completes ---
    upstream_done = fabric_lead  # fabric is the longest parallel dependency

    # Production
    production_days = max(14, -(-qty // 500))  # ceiling division
    prod_end = upstream_done + production_days
    deps.append(UpstreamDependency(
        dependency_id=f"DEP-{uuid.uuid4().hex[:6].upper()}",
        dependency_type="production",
        description=f"Garment CMT production: {qty:,} pcs, {requirements.size_range or 'mixed sizes'}",
        required_by_day=prod_end,
        estimated_lead_days=production_days,
        supplier_actor="FAC-001",
    ))

    # QC inspection
    qc_days = 3
    qc_end = prod_end + qc_days
    deps.append(UpstreamDependency(
        dependency_id=f"DEP-{uuid.uuid4().hex[:6].upper()}",
        dependency_type="qc_inspection",
        description=f"{requirements.qc_standard or 'AQL 2.5'} final inspection + inline QC",
        required_by_day=qc_end,
        estimated_lead_days=qc_days,
        supplier_actor="QC-001",
    ))

    # Logistics / export
    logistics_days = 7
    total_days = qc_end + logistics_days
    risk_flags_log: list[str] = []
    if total_days > deadline:
        risk_flags_log.append(f"total_exceeds_deadline_{deadline}d_by_{total_days - deadline}d")

    deps.append(UpstreamDependency(
        dependency_id=f"DEP-{uuid.uuid4().hex[:6].upper()}",
        dependency_type="logistics",
        description=f"{requirements.trade_term or 'FOB'} shipment booking and export documentation",
        required_by_day=total_days,
        estimated_lead_days=logistics_days,
        supplier_actor="LOG-001",
        risk_flags=risk_flags_log,
    ))

    return deps


def generate_supplier_inquiries(
    requirements: ExtractedRequirements,
    m_roles: list[MRoleContext],
) -> list[dict]:
    """
    Generate structured supplier inquiry templates for upstream outreach.
    """
    inquiries: list[dict] = []

    # Fabric supplier inquiry
    inquiries.append({
        "inquiry_id": f"SUP-INQ-{uuid.uuid4().hex[:6].upper()}",
        "target_role": "fabric_supplier",
        "subject": f"RFQ: {requirements.fabric_type or 'cotton'} fabric — {requirements.quantity or 10000:,} pcs",
        "body": (
            f"Dear Fabric Supplier,\n\n"
            f"We require fabric for an apparel export order with the following specifications:\n"
            f"  Product: {requirements.product_type or 'Shirt'}\n"
            f"  Fabric: {requirements.fabric_type or '100% cotton'}"
            + (f", {requirements.fabric_weight_gsm}gsm" if requirements.fabric_weight_gsm else "")
            + f"\n"
            f"  Quantity: approx. {requirements.quantity or 10000:,} pieces ({requirements.size_range or 'S/M/L/XL'})\n"
            f"  Colors: {requirements.color or 'White, Light Blue'}\n"
            f"  FOB Deadline: {requirements.delivery_deadline_days or 45} days from order confirmation\n"
            f"  Target Market: {requirements.target_market or 'Japan'}\n\n"
            f"Please provide:\n"
            f"  1. Unit price per meter (USD)\n"
            f"  2. Lead time in days\n"
            f"  3. MOQ in meters\n"
            f"  4. Color availability confirmation\n"
            f"  5. Certifications (OEKO-TEX, REACH compliance)\n\n"
            f"Thank you."
        ),
        "required_fields_from_supplier": [
            "unit_price_per_meter_usd",
            "lead_time_days",
            "moq_meters",
            "color_availability",
            "certification",
        ],
    })

    # Garment factory inquiry
    inquiries.append({
        "inquiry_id": f"SUP-INQ-{uuid.uuid4().hex[:6].upper()}",
        "target_role": "garment_factory",
        "subject": (
            f"RFQ: CMT production — {requirements.quantity or 10000:,} pcs "
            f"{requirements.product_type or 'Shirt'}"
        ),
        "body": (
            f"Dear Production Partner,\n\n"
            f"We are seeking manufacturing capacity for the following export order:\n"
            f"  Product: {requirements.product_type or 'Cotton Shirt'}\n"
            f"  Quantity: {requirements.quantity or 10000:,} pcs, sizes {requirements.size_range or 'S/M/L/XL'}\n"
            f"  Fabric: GFT (fabric supplied by us) — {requirements.fabric_type or '100% cotton'}\n"
            f"  Colors: {requirements.color or 'White, Light Blue'}\n"
            f"  Required: {requirements.trade_term or 'FOB'} within {requirements.delivery_deadline_days or 45} days\n"
            f"  QC Standard: {requirements.qc_standard or 'AQL 2.5'}\n"
            f"  Target Market: {requirements.target_market or 'Japan'}\n\n"
            f"Please quote:\n"
            f"  1. CM price per piece (USD)\n"
            f"  2. Production lead time (days)\n"
            f"  3. Daily production capacity (pieces/day)\n"
            f"  4. Earliest available production slot\n"
            f"  5. QC and inspection compliance confirmation\n\n"
            f"Thank you."
        ),
        "required_fields_from_supplier": [
            "cm_price_per_piece_usd",
            "production_lead_time_days",
            "daily_capacity_pcs",
            "earliest_start_date",
            "qc_compliance",
        ],
    })

    return inquiries


def plan_upstream(requirements: ExtractedRequirements) -> UpstreamPlan:
    """
    Full upstream planning: M-side role resolution, dependency planning,
    and supplier inquiry generation.
    """
    m_roles = resolve_m_side_roles(requirements)
    dependencies = plan_upstream_dependencies(requirements)
    supplier_inquiries = generate_supplier_inquiries(requirements, m_roles)

    total_days = max((dep.required_by_day for dep in dependencies), default=45)

    return UpstreamPlan(
        plan_id=f"PLAN-{uuid.uuid4().hex[:8].upper()}",
        inquiry_id=requirements.inquiry_id,
        m_roles=m_roles,
        dependencies=dependencies,
        supplier_inquiries=supplier_inquiries,
        total_upstream_days_estimate=total_days,
    )
