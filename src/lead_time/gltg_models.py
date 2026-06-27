"""GLTG data-transfer objects (DTOs).

These are plain data containers only -- no calculation. They describe the input
abcdYi assembles from its database and the feasibility result it persists. All
lead-time / path / feasibility calculation is owned by the standalone GLTG
service (https://github.com/GiraffeTechnology/GLTG) and reached through
``src.integrations.gltg_client``.

(Previously these classes lived in the now-removed vendored GLTG engine.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class ParticipantNode:
    participant_id: str
    role: str
    fabric_lead_time_days: Optional[int] = None
    trim_lead_time_days: Optional[int] = None
    packaging_lead_time_days: Optional[int] = None
    production_time_days: Optional[int] = None
    qc_time_days: Optional[int] = None
    logistics_time_days: Optional[int] = None
    supplier_stated_lead_time_days: Optional[int] = None
    moq: Optional[int] = None
    capacity_available: Optional[bool] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    craft_process: Optional[str] = None
    qc_pass_rate: Optional[float] = None
    on_time_delivery_rate: Optional[float] = None
    quality_issue_count: int = 0


@dataclass
class DependencyEdge:
    from_node_id: str
    to_node_id: str
    dependency_type: str
    lag_days: int = 0


@dataclass
class ApparelOrderInput:
    order_id: str
    required_delivery_date: Optional[date] = None
    quantity: int = 0
    product_categories: list[str] = field(default_factory=list)
    participant_nodes: list[ParticipantNode] = field(default_factory=list)
    dependency_edges: list[DependencyEdge] = field(default_factory=list)
    milestone_updates: list[dict] = field(default_factory=list)
    form_fields: dict = field(default_factory=dict)
    evaluated_at: Optional[datetime] = None


@dataclass
class DeliveryPath:
    path_id: str
    participant_ids: list[str]
    parallel_max_days: Optional[int]
    sequential_days: Optional[int]
    total_lead_time_days: Optional[int]
    earliest_delivery_date: Optional[date]
    most_likely_delivery_date: Optional[date]
    risk_adjusted_delivery_date: Optional[date]
    committable_delivery_date: Optional[date]
    critical_path: list[str]
    critical_path_days: Optional[int]
    is_feasible: bool
    feasibility_reason: str
    risk_flags: list[str]
    missing_evidence: list[str]
    unit_price: Optional[float]
    currency: Optional[str]
    rank_score: float = 0.0
    recommendation_reason: str = ""
    confidence: str = "LOW"


@dataclass
class DeliveryFeasibilityPacket:
    order_id: str
    source: str = "GLTG"
    status: str = "EVALUATED"
    earliest_delivery_date: Optional[date] = None
    most_likely_delivery_date: Optional[date] = None
    risk_adjusted_delivery_date: Optional[date] = None
    committable_delivery_date: Optional[date] = None
    required_delivery_date: Optional[date] = None
    delivery_feasibility: str = "UNKNOWN"
    days_vs_deadline: Optional[int] = None
    critical_path: list[str] = field(default_factory=list)
    critical_path_days: Optional[int] = None
    ranked_options: list[DeliveryPath] = field(default_factory=list)
    option_count: int = 0
    risk_flags: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    explanation: str = ""
    confidence: str = "LOW"
