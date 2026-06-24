from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class GPMQuoteGuidancePacket:
    packet_id: str
    tenant_id: str | None
    project_id: str | None
    rfq_id: str | None
    supplier_response_id: str | None
    context_bundle_id: str | None
    evidence_ids: list[str]
    supplier_quote_position: str
    recommendation: str
    benchmark_range: dict
    negotiation_points: list[str]
    buyer_quote_options: list[dict]
    runtime_profile: str
    runtime_mode: str
    context_retriever: str
    data_mode: str
    human_approval_required: bool
    operator_action_required: bool
    approval_status: str  # pending | approved | rejected | expired | superseded
    audit_ref: str | None
    created_at: str

    def __post_init__(self) -> None:
        if not self.human_approval_required:
            raise ValueError("human_approval_required must always be True")
        valid = {"pending", "approved", "rejected", "expired", "superseded"}
        if self.approval_status not in valid:
            raise ValueError(f"approval_status must be one of {valid}")

    @classmethod
    def create(
        cls,
        *,
        supplier_quote_position: str,
        recommendation: str,
        benchmark_range: dict,
        negotiation_points: list[str],
        buyer_quote_options: list[dict],
        runtime_profile: str,
        runtime_mode: str,
        context_retriever: str,
        data_mode: str,
        operator_action_required: bool = True,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        context_bundle_id: str | None = None,
        evidence_ids: list[str] | None = None,
        audit_ref: str | None = None,
    ) -> "GPMQuoteGuidancePacket":
        return cls(
            packet_id=f"gpm_pkt_{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            project_id=project_id,
            rfq_id=rfq_id,
            supplier_response_id=supplier_response_id,
            context_bundle_id=context_bundle_id,
            evidence_ids=evidence_ids or [],
            supplier_quote_position=supplier_quote_position,
            recommendation=recommendation,
            benchmark_range=benchmark_range,
            negotiation_points=negotiation_points,
            buyer_quote_options=buyer_quote_options,
            runtime_profile=runtime_profile,
            runtime_mode=runtime_mode,
            context_retriever=context_retriever,
            data_mode=data_mode,
            human_approval_required=True,
            operator_action_required=operator_action_required,
            approval_status="pending",
            audit_ref=audit_ref,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "rfq_id": self.rfq_id,
            "supplier_response_id": self.supplier_response_id,
            "context_bundle_id": self.context_bundle_id,
            "evidence_ids": self.evidence_ids,
            "supplier_quote_position": self.supplier_quote_position,
            "recommendation": self.recommendation,
            "benchmark_range": self.benchmark_range,
            "negotiation_points": self.negotiation_points,
            "buyer_quote_options": self.buyer_quote_options,
            "runtime_profile": self.runtime_profile,
            "runtime_mode": self.runtime_mode,
            "context_retriever": self.context_retriever,
            "data_mode": self.data_mode,
            "human_approval_required": self.human_approval_required,
            "operator_action_required": self.operator_action_required,
            "approval_status": self.approval_status,
            "audit_ref": self.audit_ref,
            "created_at": self.created_at,
        }
