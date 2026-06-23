from __future__ import annotations

from typing import Any

from src.gpm.context.gpm_context_bundle import GPMContextBundle

_FORBIDDEN_PATTERNS = (
    "place order",
    "place_order",
    "dispatch quote",
    "dispatch_quote",
    "send quote to buyer",
    "make payment",
    "payment instruction",
    "auto dispatch",
    "auto_dispatch",
    "buyer quote dispatch",
    "approve_order",
)

_REQUIRED_KEYS = frozenset({
    "normalized_product_type",
    "is_comparable",
    "comparability_score",
    "evidence_ids",
    "reason",
    "confidence",
})


class QwenOutputValidationError(ValueError):
    pass


def validate_qwen_output(output: Any, context: GPMContextBundle) -> None:
    """Validate Qwen JSON output against a context bundle.

    Raises QwenOutputValidationError on any violation.
    """
    if not isinstance(output, dict):
        raise QwenOutputValidationError(
            f"Qwen output must be a JSON object (dict), got {type(output).__name__}."
        )

    missing = _REQUIRED_KEYS - output.keys()
    if missing:
        raise QwenOutputValidationError(
            f"Qwen output missing required keys: {sorted(missing)}"
        )

    score = output.get("comparability_score")
    if not isinstance(score, (int, float)):
        raise QwenOutputValidationError(
            f"comparability_score must be numeric, got {type(score).__name__}."
        )
    if not (0.0 <= float(score) <= 1.0):
        raise QwenOutputValidationError(
            f"comparability_score must be between 0 and 1, got {score}."
        )

    cited_ids = output.get("evidence_ids", [])
    if not isinstance(cited_ids, list):
        raise QwenOutputValidationError("evidence_ids must be a list.")

    valid_ids = context.evidence_ids()
    unknown = [eid for eid in cited_ids if eid not in valid_ids]
    if unknown:
        raise QwenOutputValidationError(
            f"Qwen output cites unknown evidence IDs: {unknown}. "
            f"Valid IDs: {sorted(valid_ids)}"
        )

    if "invented_price" in output:
        raise QwenOutputValidationError(
            "Qwen output must not contain invented_price field."
        )
    if "invented_moq" in output:
        raise QwenOutputValidationError(
            "Qwen output must not contain invented_moq field."
        )

    if output.get("dispatch_buyer_quote") is True:
        raise QwenOutputValidationError(
            "Qwen output must not set dispatch_buyer_quote=True."
        )
    if output.get("approve_order") is True:
        raise QwenOutputValidationError(
            "Qwen output must not approve orders directly."
        )

    output_str = str(output).lower()
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in output_str:
            raise QwenOutputValidationError(
                f"Qwen output contains forbidden instruction: '{pattern}'."
            )
