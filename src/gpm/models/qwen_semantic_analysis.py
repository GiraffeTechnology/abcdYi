from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class QwenSemanticAnalysis(BaseModel):
    """Schema-validated output from a local Qwen semantic analysis call.

    Must not include final buyer quote price, order, or payment instructions.
    """

    normalized_product_type: str
    normalized_material: str | None = None
    normalized_process_tags: list[str] = []
    is_comparable: bool
    comparability_score: float
    detected_mismatch_flags: list[str] = []
    evidence_ids: list[str] = []
    reason: str
    confidence: Literal["low", "medium", "high"]

    @field_validator("comparability_score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"comparability_score must be between 0 and 1, got {v}"
            )
        return v
