from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class QwenSemanticAnalysis(BaseModel):
    normalized_product_type: str
    normalized_material: str | None = None
    normalized_process_tags: list[str] = Field(default_factory=list)
    is_comparable: bool
    comparability_score: float
    detected_mismatch_flags: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str
    confidence: Literal["low", "medium", "high"]

    @field_validator("comparability_score")
    @classmethod
    def _validate_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"comparability_score must be between 0 and 1, got {v}")
        return v
