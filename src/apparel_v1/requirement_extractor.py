"""
Requirement extraction for the apparel/textile v1 E2E flow.
Extracts structured requirements from buyer inquiry text using deterministic
rule-based parsing (offline / test mode). Pass a real LLM provider for production.
"""
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.apparel_v1.inquiry_intake import BuyerInquiry
from src.llm.mock_provider import MockLLMProvider
from src.llm.provider_base import MultimodalLLMProviderBase


@dataclass
class ExtractedRequirements:
    inquiry_id: str
    product_type: Optional[str] = None
    product_category: Optional[str] = None
    quantity: Optional[int] = None
    fabric_type: Optional[str] = None
    fabric_composition: Optional[str] = None
    fabric_weight_gsm: Optional[int] = None
    color: Optional[str] = None
    size_range: Optional[str] = None
    size_breakdown: Optional[dict] = None
    pattern_or_cutting_requirement: Optional[str] = None
    trim_requirement: Optional[str] = None
    label_requirement: Optional[str] = None
    washing_mark_requirement: Optional[str] = None
    packaging_requirement: Optional[str] = None
    qc_standard: Optional[str] = None
    sample_requirement: Optional[str] = None
    delivery_deadline: Optional[str] = None
    delivery_deadline_days: Optional[int] = None
    trade_term: Optional[str] = None
    destination: Optional[str] = None
    payment_term: Optional[str] = None
    compliance_requirement: Optional[str] = None
    special_notes: Optional[str] = None
    target_market: Optional[str] = None
    ai_generated: bool = True
    extraction_id: str = field(default_factory=lambda: f"EXT-{uuid.uuid4().hex[:8].upper()}")


_PRODUCT_KEYWORDS = [
    "shirt", "t-shirt", "tshirt", "polo", "jacket", "coat",
    "trousers", "pants", "jeans", "dress", "skirt", "blouse",
    "sweater", "hoodie", "vest", "shorts", "uniform",
]

_FABRIC_KEYWORDS = {
    "cotton": "100% cotton",
    "polyester": "polyester",
    "nylon": "nylon",
    "linen": "linen",
    "wool": "wool",
    "silk": "silk",
    "rayon": "rayon",
    "spandex": "spandex",
    "denim": "denim",
}

_COLOR_KEYWORDS = [
    "white", "black", "grey", "gray", "navy", "blue", "light blue",
    "red", "green", "yellow", "orange", "purple", "pink", "brown",
    "beige", "khaki", "olive",
]

_TRADE_TERMS = ["fob", "cif", "exw", "ddp", "cfr", "dap"]

_MARKET_KEYWORDS = {
    "japan": "Japan",
    "usa": "USA",
    "us ": "USA",
    "europe": "Europe",
    "eu ": "Europe",
    "uk": "UK",
    "australia": "Australia",
    "korea": "Korea",
}


def extract_requirements(
    inquiry: BuyerInquiry,
    provider: Optional[MultimodalLLMProviderBase] = None,
) -> ExtractedRequirements:
    """
    Extract structured requirements from a buyer inquiry.

    In offline/test mode (default): deterministic rule-based extraction.
    In production: pass a real LLM provider for arbitrary-text extraction.
    """
    if provider is None:
        provider = MockLLMProvider()

    req = _extract_deterministic(inquiry.raw_text)
    req.inquiry_id = inquiry.inquiry_id
    return req


def _extract_deterministic(raw_text: str) -> ExtractedRequirements:
    """Rule-based extraction covering the canonical apparel inquiry and variants."""
    text_lower = raw_text.lower()
    req = ExtractedRequirements(inquiry_id="")

    # Quantity — match "10,000 pcs", "10000 cotton shirts", "5000 polyester jackets"
    # Try strict pattern first (number immediately before unit keyword)
    qty_match = re.search(
        r"(\d[\d,]*)\s*(?:pcs?|pieces?|units?|shirts?|jackets?|garments?|pairs?)",
        text_lower,
    )
    if not qty_match:
        # Allow 1–3 intervening words (e.g. "10,000 cotton shirts")
        qty_match = re.search(
            r"(\d[\d,]+)\s+(?:\w+\s+){1,3}(?:pcs?|pieces?|units?|shirts?|jackets?|"
            r"garments?|pairs?|dresses?|trousers?|pants?|coats?|hoodies?|blouses?|skirts?)",
            text_lower,
        )
    if qty_match:
        req.quantity = int(qty_match.group(1).replace(",", ""))

    # Product type
    for product in _PRODUCT_KEYWORDS:
        if product in text_lower:
            req.product_type = product.title()
            break

    # Fabric type
    fabric_found = None
    for kw, canonical in _FABRIC_KEYWORDS.items():
        if kw in text_lower:
            fabric_found = canonical
            break
    if fabric_found:
        req.fabric_type = fabric_found
        req.fabric_composition = fabric_found
        if "cotton" in fabric_found:
            req.fabric_weight_gsm = 180

    # Colors — scan for multi-color specifications
    found_colors = []
    for color in _COLOR_KEYWORDS:
        if color in text_lower:
            found_colors.append(color)
    if found_colors:
        req.color = ", ".join(found_colors)

    # Size range
    if "s/m/l/xl" in text_lower or "s, m, l, xl" in text_lower:
        req.size_range = "S/M/L/XL"
        if req.quantity:
            q = req.quantity
            req.size_breakdown = {
                "S": int(q * 0.20),
                "M": int(q * 0.30),
                "L": int(q * 0.30),
                "XL": int(q * 0.20),
            }
    elif "xs" in text_lower and "xxl" in text_lower:
        req.size_range = "XS-XXL"
    elif "m-xxl" in text_lower or "m to xxl" in text_lower:
        req.size_range = "M-XXL"

    # Delivery deadline — "within 45 days" or "in 60 days"
    days_match = re.search(r"(?:within|in)\s+(\d+)\s*days?", text_lower)
    if days_match:
        d = int(days_match.group(1))
        req.delivery_deadline = f"{d} days"
        req.delivery_deadline_days = d

    # Trade term
    for term in _TRADE_TERMS:
        if term in text_lower:
            req.trade_term = term.upper()
            break

    # Destination / origin
    if "china" in text_lower:
        req.destination = "China (port TBC)"

    # Target market
    for kw, market in _MARKET_KEYWORDS.items():
        if kw in text_lower:
            req.target_market = market
            break

    # Special notes
    notes_parts = []
    if "export" in text_lower:
        notes_parts.append("Export order")
    if req.target_market:
        notes_parts.append(f"target market {req.target_market}")
    req.special_notes = ", ".join(notes_parts) if notes_parts else None

    # Defaults for apparel orders
    req.qc_standard = "AQL 2.5"
    req.product_category = "unisex"

    return req
