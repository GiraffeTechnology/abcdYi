from __future__ import annotations

from src.gpm.context.gpm_context_bundle import GPMContextBundle

_FORBIDDEN_PATTERNS = (
    "dispatch quote",
    "send quote to buyer",
    "place order",
    "make payment",
    "execute payment",
    "approve order",
    "auto-approve",
    "automatically approved",
)

REQUIRED_KEYS = {
    "normalized_product_type",
    "is_comparable",
    "comparability_score",
    "evidence_ids",
    "reason",
    "confidence",
}


class QwenOutputValidationError(ValueError):
    pass


class QwenOutputValidator:
    """Validate Qwen JSON output against the context bundle and safety rules."""

    def validate(self, output: object, context: GPMContextBundle) -> None:
        if not isinstance(output, dict):
            raise QwenOutputValidationError("Qwen output must be a JSON object (dict).")

        missing = REQUIRED_KEYS - set(output.keys())
        if missing:
            raise QwenOutputValidationError(f"Qwen output missing required keys: {missing}")

        score = output.get("comparability_score")
        if not isinstance(score, (int, float)):
            raise QwenOutputValidationError(
                f"comparability_score must be numeric, got {type(score).__name__}"
            )
        if not (0.0 <= float(score) <= 1.0):
            raise QwenOutputValidationError(
                f"comparability_score must be between 0 and 1, got {score}"
            )

        valid_ids = context.evidence_ids()
        cited_ids = output.get("evidence_ids", [])
        if not isinstance(cited_ids, list):
            raise QwenOutputValidationError("evidence_ids must be a list.")
        for eid in cited_ids:
            if eid not in valid_ids:
                raise QwenOutputValidationError(
                    f"Qwen cited unknown evidence_id {eid!r}. "
                    "Only IDs present in the context bundle are allowed."
                )

        self._check_no_invented_prices(output)
        self._check_no_invented_moq(output)
        self._check_no_forbidden_instructions(output)

    def _check_no_invented_prices(self, output: dict) -> None:
        reason = str(output.get("reason", "")).lower()
        for field_name in ("price", "unit_price", "quote_price", "invented_price"):
            if field_name in output:
                raise QwenOutputValidationError(
                    f"Qwen output must not include a '{field_name}' field. "
                    "Price decisions are made by deterministic GPM engines."
                )

    def _check_no_invented_moq(self, output: dict) -> None:
        for field_name in ("moq", "min_order_qty", "minimum_order_quantity"):
            if field_name in output:
                raise QwenOutputValidationError(
                    f"Qwen output must not include a '{field_name}' field. "
                    "MOQ values must come from supplier evidence, not Qwen output."
                )

    def _check_no_forbidden_instructions(self, output: dict) -> None:
        text = " ".join(str(v).lower() for v in output.values() if isinstance(v, str))
        for pattern in _FORBIDDEN_PATTERNS:
            if pattern in text:
                raise QwenOutputValidationError(
                    f"Qwen output contains forbidden instruction: {pattern!r}. "
                    "Buyer-facing quote dispatch, orders, and payments require human approval."
                )
