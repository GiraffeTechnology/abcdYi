from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class ParticipantNode:
    """A supplier, workshop, or process participant in the supply network."""
    participant_id: str
    role: str  # MANUFACTURER, FABRIC_SUPPLIER, TRIM_SUPPLIER, PACKAGING_SUPPLIER, QC_INSPECTOR, LOGISTICS_PROVIDER
    # Lead time evidence (in days; None = unknown)
    fabric_lead_time_days: Optional[int] = None
    trim_lead_time_days: Optional[int] = None
    packaging_lead_time_days: Optional[int] = None
    production_time_days: Optional[int] = None
    qc_time_days: Optional[int] = None
    logistics_time_days: Optional[int] = None
    # Stated total from supplier response
    supplier_stated_lead_time_days: Optional[int] = None
    # Capacity and commercial evidence
    moq: Optional[int] = None
    capacity_available: Optional[bool] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    # Process-specific
    craft_process: Optional[str] = None
    # Reliability signals
    qc_pass_rate: Optional[float] = None
    on_time_delivery_rate: Optional[float] = None
    quality_issue_count: int = 0


@dataclass
class DependencyEdge:
    """A dependency between two supply chain nodes."""
    from_node_id: str
    to_node_id: str
    dependency_type: str  # MATERIAL_SUPPLY, TRIM_SUPPLY, PACKAGING_SUPPLY, SUBCONTRACT, SEQUENTIAL
    lag_days: int = 0


@dataclass
class ApparelOrderInput:
    """Input to GLTG for a single order evaluation."""
    order_id: str
    required_delivery_date: Optional[date] = None
    quantity: int = 0
    product_categories: list[str] = field(default_factory=list)
    # Participant nodes — one or more paths
    participant_nodes: list[ParticipantNode] = field(default_factory=list)
    # Explicit dependencies (optional — GLTG infers from roles if not provided)
    dependency_edges: list[DependencyEdge] = field(default_factory=list)
    # Milestone evidence (current state of production)
    milestone_updates: list[dict] = field(default_factory=list)
    # Form fields (structured order requirements)
    form_fields: dict = field(default_factory=dict)
    # Evaluation date
    evaluated_at: Optional[datetime] = None


@dataclass
class DeliveryPath:
    """A single feasible (or evaluated) delivery path through the supply network."""
    path_id: str
    participant_ids: list[str]
    # Lead time breakdown
    parallel_max_days: Optional[int]
    sequential_days: Optional[int]
    total_lead_time_days: Optional[int]
    # Dates
    earliest_delivery_date: Optional[date]
    most_likely_delivery_date: Optional[date]
    risk_adjusted_delivery_date: Optional[date]
    committable_delivery_date: Optional[date]
    # Critical path
    critical_path: list[str]
    critical_path_days: Optional[int]
    # Feasibility
    is_feasible: bool
    feasibility_reason: str
    # Risks
    risk_flags: list[str]
    missing_evidence: list[str]
    # Cost
    unit_price: Optional[float]
    currency: Optional[str]
    # Ranking score (higher = better)
    rank_score: float = 0.0
    recommendation_reason: str = ""
    # GLTG internals
    confidence: str = "LOW"  # LOW | MEDIUM | HIGH


@dataclass
class DeliveryFeasibilityPacket:
    """Output from GLTG engine.evaluate()."""
    order_id: str
    source: str = "GLTG"
    status: str = "EVALUATED"  # EVALUATED | INFEASIBLE | INCOMPLETE_EVIDENCE
    # Overall dates (from best feasible path)
    earliest_delivery_date: Optional[date] = None
    most_likely_delivery_date: Optional[date] = None
    risk_adjusted_delivery_date: Optional[date] = None
    committable_delivery_date: Optional[date] = None
    required_delivery_date: Optional[date] = None
    # Will it make the deadline?
    delivery_feasibility: str = "UNKNOWN"  # FEASIBLE | AT_RISK | INFEASIBLE | UNKNOWN
    days_vs_deadline: Optional[int] = None  # negative = ahead, positive = behind
    # Critical path
    critical_path: list[str] = field(default_factory=list)
    critical_path_days: Optional[int] = None
    # Ranked options (up to N — never faked)
    ranked_options: list[DeliveryPath] = field(default_factory=list)
    option_count: int = 0
    # Risk and evidence
    risk_flags: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    # Human-readable explanation
    explanation: str = ""
    # Confidence
    confidence: str = "LOW"
