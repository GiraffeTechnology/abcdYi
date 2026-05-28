from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from src.db.models.dynamic_schema import (
    SchemaRegistry, FieldDefinition, ObservedField, FieldProposal,
    EntityDynamicValue, FieldPromotionDecision
)
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


PROPOSAL_THRESHOLDS = {
    "min_projects": 5,
    "min_suppliers": 3,
    "min_confidence": 0.85,
}

AUTO_APPROVE_RISK_LEVELS = {"low"}
AUTO_APPROVE_MIN_EXAMPLES = 3


class DynamicSchemaRepo:
    def __init__(self, db: Session):
        self.db = db

    def observe_field(
        self,
        candidate_field_name: str,
        confidence_score: float,
        project_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        source_message_id: Optional[str] = None,
        source_artifact_id: Optional[str] = None,
        normalized_field_name: Optional[str] = None,
        candidate_value: Optional[str] = None,
        candidate_unit: Optional[str] = None,
        normalized_value: Optional[str] = None,
        evidence_text: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> ObservedField:
        now = _utcnow()
        obs = ObservedField(
            observed_field_id=new_uuid(),
            project_id=project_id,
            actor_id=actor_id,
            source_message_id=source_message_id,
            source_artifact_id=source_artifact_id,
            candidate_field_name=candidate_field_name,
            normalized_field_name=normalized_field_name or candidate_field_name.lower().replace(" ", "_"),
            candidate_value=candidate_value,
            candidate_unit=candidate_unit,
            normalized_value=normalized_value,
            confidence_score=confidence_score,
            evidence_text=evidence_text,
            created_at=now,
            metadata_json=metadata_json or {},
        )
        self.db.add(obs)
        self.db.flush()
        return obs

    def propose_field(
        self,
        schema_id: str,
        candidate_field_name: str,
        normalized_field_name: str,
        field_type: str,
        suggested_unit: Optional[str] = None,
        business_reason: Optional[str] = None,
        example_count: int = 0,
        project_count: int = 0,
        supplier_count: int = 0,
        confidence_score: float = 0.0,
        risk_level: str = "low",
        metadata_json: Optional[dict] = None,
    ) -> FieldProposal:
        now = _utcnow()
        proposal = FieldProposal(
            proposal_id=new_uuid(),
            schema_id=schema_id,
            candidate_field_name=candidate_field_name,
            normalized_field_name=normalized_field_name,
            field_type=field_type,
            suggested_unit=suggested_unit,
            business_reason=business_reason,
            example_count=example_count,
            project_count=project_count,
            supplier_count=supplier_count,
            confidence_score=confidence_score,
            risk_level=risk_level,
            status="proposed",
            created_at=now,
            updated_at=now,
            metadata_json=metadata_json or {},
        )
        self.db.add(proposal)
        self.db.flush()
        return proposal

    def approve_field(
        self,
        proposal_id: str,
        schema_id: str,
        decided_by: str = "human",
        reason: Optional[str] = None,
    ) -> Optional[FieldDefinition]:
        proposal = self.db.query(FieldProposal).filter(
            FieldProposal.proposal_id == proposal_id
        ).first()
        if not proposal:
            return None

        # Record the decision
        decision = FieldPromotionDecision(
            decision_id=new_uuid(),
            proposal_id=proposal_id,
            decision="approved",
            decided_by=decided_by,
            reason=reason,
            created_at=_utcnow(),
            metadata_json={},
        )
        self.db.add(decision)

        # Promote to field_definition
        now = _utcnow()
        field_def = FieldDefinition(
            field_id=new_uuid(),
            schema_id=schema_id,
            field_name=proposal.candidate_field_name,
            normalized_field_name=proposal.normalized_field_name,
            field_type=proposal.field_type,
            unit=proposal.suggested_unit,
            description=proposal.business_reason,
            required_level="learned",
            validation_rule_json={},
            example_values_json={},
            source="dynamic_learning",
            status="approved",
            created_at=now,
            updated_at=now,
        )
        self.db.add(field_def)

        proposal.status = "approved"
        proposal.updated_at = now
        self.db.flush()
        return field_def

    def can_auto_approve(self, proposal: FieldProposal) -> bool:
        return (
            proposal.risk_level in AUTO_APPROVE_RISK_LEVELS
            and proposal.example_count >= AUTO_APPROVE_MIN_EXAMPLES
        )

    def store_dynamic_value(
        self,
        entity_type: str,
        entity_id: str,
        field_id: str,
        field_value: str,
        unit: Optional[str] = None,
        confidence_score: float = 0.0,
        source: Optional[str] = None,
        source_message_id: Optional[str] = None,
        source_artifact_id: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> EntityDynamicValue:
        now = _utcnow()
        val = EntityDynamicValue(
            value_id=new_uuid(),
            entity_type=entity_type,
            entity_id=entity_id,
            field_id=field_id,
            field_value=field_value,
            unit=unit,
            confidence_score=confidence_score,
            source=source,
            source_message_id=source_message_id,
            source_artifact_id=source_artifact_id,
            created_at=now,
            metadata_json=metadata_json or {},
        )
        self.db.add(val)
        self.db.flush()
        return val

    def list_schema_fields(self, schema_id: str) -> List[FieldDefinition]:
        return self.db.query(FieldDefinition).filter(
            FieldDefinition.schema_id == schema_id
        ).all()

    def get_schema_by_industry_category(
        self, industry: str, category: str
    ) -> Optional[SchemaRegistry]:
        return self.db.query(SchemaRegistry).filter(
            SchemaRegistry.industry == industry,
            SchemaRegistry.category == category,
        ).first()
