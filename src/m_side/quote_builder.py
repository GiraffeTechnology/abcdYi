"""
M-side quote builder — extracts SupplierQuote fields from supplier text.
"""

import re
from src.core_schema.m_side_types import SupplierQuote
from src.m_side.response_normalizer import _parse_unit_price, _parse_moq


def build_supplier_quote(response_texts: list[str]) -> SupplierQuote:
    """
    Extract quote fields from supplier message text.
    Completeness increases with each filled field.
    """
    combined = " ".join(response_texts)

    unit_price, currency = _parse_unit_price(combined)
    moq = _parse_moq(combined)

    # Tooling fee
    tooling_fee = None
    tf_match = re.search(
        r"(?:模具费|tooling fee|mold fee)\s*[:：]?\s*(\d+\.?\d*)\s*(USD|RMB|CNY|元|美元)?",
        combined,
        re.IGNORECASE,
    )
    if tf_match:
        tooling_fee = float(tf_match.group(1))

    # Sample fee
    sample_fee = None
    sf_match = re.search(
        r"(?:打样费|样品费|sample fee)\s*[:：]?\s*(\d+\.?\d*)\s*(USD|RMB|CNY|元|美元)?",
        combined,
        re.IGNORECASE,
    )
    if sf_match:
        sample_fee = float(sf_match.group(1))

    # Price validity
    price_valid = None
    pv_match = re.search(r"(?:报价有效期|price valid).*?(\d+)\s*(?:天|days?)", combined, re.IGNORECASE)
    if pv_match:
        price_valid = f"{pv_match.group(1)} days"

    # Quote notes
    notes_parts = []
    if moq:
        notes_parts.append(f"MOQ: {moq}")
    if re.search(r"阳极氧化|anodizing", combined, re.IGNORECASE):
        notes_parts.append("anodizing included")
    if re.search(r"外协|outsourc", combined, re.IGNORECASE):
        notes_parts.append("outsourced process")

    return SupplierQuote(
        currency=currency,
        unit_price=unit_price,
        total_price=(unit_price * 500) if unit_price else None,  # 500 qty default
        tooling_fee=tooling_fee,
        sample_fee=sample_fee,
        price_valid_until=price_valid,
        quote_notes="; ".join(notes_parts) if notes_parts else None,
    )
