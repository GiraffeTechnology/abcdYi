from __future__ import annotations

from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample


def validate_sample(sample: GPMSupplierPriceSample) -> None:
    """Apply required-field rules and set usability flags in place."""
    sample.invalid_reasons = []

    if not sample.supplier_id:
        sample.invalid_reasons.append("missing_supplier_id")

    if not sample.captured_at and not sample.observed_at:
        sample.invalid_reasons.append("missing_observed_time")

    if sample.moq is None:
        sample.invalid_reasons.append("missing_moq")

    if not sample.price_min and not sample.ladder_prices:
        sample.invalid_reasons.append("missing_price")

    sample.usable_for_benchmark = len(sample.invalid_reasons) == 0
    sample.usable_for_quote_guidance = len(sample.invalid_reasons) == 0
