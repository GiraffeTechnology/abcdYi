from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QwenSemanticAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    normalized_product_type: str
    normalized_material: str | None = None
    normalized_process_tags: list[str] = Field(default_factory=list)
    is_comparable: bool
    comparability_score: float
    detected_mismatch_flags: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    risk_explanation: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str
    confidence: Literal["low", "medium", "high"]
    human_approval_required: bool = True

    @field_validator("comparability_score")
    @classmethod
    def _validate_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"comparability_score must be between 0 and 1, got {v}")
        return v

    @field_validator("human_approval_required")
    @classmethod
    def _must_be_true(cls, v: bool) -> bool:
        if not v:
            raise ValueError("human_approval_required must always be True")
        return v
