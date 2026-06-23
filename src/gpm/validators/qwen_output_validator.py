from __future__ import annotations

from src.gpm.context.gpm_context_bundle import GPMContextBundle

VALID_RECOMMENDATIONS = frozenset({
    "accept",
    "negotiate",
    "reject",
    "request_more_info",
    "human_review_required",
})

VALID_POSITIONS = frozenset({
    "below_market",
    "within_low_range",
    "within_mid_range",
    "within_high_range",
    "above_market",
    "insufficient_data",
})

_FORBIDDEN_TEXT_PATTERNS = (
    "dispatch quote",
    "send quote to buyer",
    "place order",
    "make payment",
    "execute payment",
    "approve order",
    "auto-approve",
    "automatically approved",
)

# These keys must never appear in Qwen output — they indicate unauthorized business actions.
_FORBIDDEN_KEYS = frozenset({
    "send_quote",
    "dispatch_quote",
    "place_order",
    "make_payment",
    "auto_approve",
})

REQUIRED_KEYS = {
    "normalized_product_type",
    "is_comparable",
    "comparability_score",
    "evidence_ids",
    "reason",
    "confidence",
    "human_approval_required",
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

        # human_approval_required must always be True — no exceptions
        if output.get("human_approval_required") is not True:
            raise QwenOutputValidationError(
                "human_approval_required must be True in Qwen output. "
                "Qwen must not authorize commercial actions without human review."
            )

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
        self._check_no_forbidden_keys(output)
        self._check_no_forbidden_instructions(output)

    def _check_no_invented_prices(self, output: dict) -> None:
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

    def _check_no_forbidden_keys(self, output: dict) -> None:
        present = _FORBIDDEN_KEYS & set(output.keys())
        if present:
            raise QwenOutputValidationError(
                f"Qwen output contains forbidden action key(s): {sorted(present)}. "
                "Buyer-facing quote dispatch, orders, and payments require human approval."
            )

    def _check_no_forbidden_instructions(self, output: dict) -> None:
        text = " ".join(str(v).lower() for v in output.values() if isinstance(v, str))
        for pattern in _FORBIDDEN_TEXT_PATTERNS:
            if pattern in text:
                raise QwenOutputValidationError(
                    f"Qwen output contains forbidden instruction: {pattern!r}. "
                    "Buyer-facing quote dispatch, orders, and payments require human approval."
                )


class GPMServiceOutputValidator:
    """Validate the combined service output dict.

    Checks Qwen semantic analysis fields PLUS Session B guidance fields merged
    into a single output. Ensures human_approval_required is always True,
    and recommendation/position values are from the allowed sets.
    """

    def validate(self, output: dict, bundle: GPMContextBundle) -> None:
        QwenOutputValidator().validate(output, bundle)

        if not output.get("human_approval_required"):
            raise QwenOutputValidationError(
                "human_approval_required must be True in service output."
            )

        recommendation = output.get("accept_recommendation")
        if recommendation is not None and recommendation not in VALID_RECOMMENDATIONS:
            raise QwenOutputValidationError(
                f"accept_recommendation {recommendation!r} is not a valid value. "
                f"Must be one of: {sorted(VALID_RECOMMENDATIONS)}"
            )

        position = output.get("supplier_quote_position")
        if position is not None and position not in VALID_POSITIONS:
            raise QwenOutputValidationError(
                f"supplier_quote_position {position!r} is not a valid value. "
                f"Must be one of: {sorted(VALID_POSITIONS)}"
            )
