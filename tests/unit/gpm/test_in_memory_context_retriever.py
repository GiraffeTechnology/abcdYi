from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample
from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever


def _make_shirt_sample(i: int, usable: bool = True) -> GPMSupplierPriceSample:
    sample = GPMSupplierPriceSample(
        id=f"sample_{i:03d}",
        source_platform="1688_mock",
        source_offer_id=f"offer_{i:03d}",
        supplier_id=f"sup_{i:03d}",
        supplier_name=f"Supplier {i}",
        supplier_location="Guangzhou",
        captured_at=datetime.now(timezone.utc),
        observed_at=datetime.now(timezone.utc),
        product_title="Men's 100% Cotton OEM Shirt",
        product_url=None,
        image_url=None,
        category_id="apparel",
        category_name="Men's Shirts",
        material="100% cotton",
        process_tags=["oem"],
        customization_supported=True,
        price_min=Decimal("32.0"),
        price_max=Decimal("38.0"),
        price_currency="CNY",
        price_unit="piece",
        moq=Decimal("500"),
        moq_unit="pieces",
        ladder_prices=[],
        sku_attributes={},
        delivery_region="Japan",
        lead_time_text="30-45 days",
        raw_response_id="raw_001",
        created_at=datetime.now(timezone.utc),
    )
    sample.usable_for_benchmark = usable
    if not usable:
        sample.invalid_reasons = ["missing_price"]
    return sample


REQUIREMENT = {
    "product_type": "men_cotton_shirt",
    "material": "100% cotton",
    "quantity": 10000,
    "unit": "piece",
}


def test_samples_converted_to_evidence():
    samples = [_make_shirt_sample(i) for i in range(1, 4)]
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(requirement=REQUIREMENT)
    assert len(context.evidence) == 3
    ids = context.evidence_ids()
    assert "ev_sample_001" in ids
    assert "ev_sample_002" in ids
    assert "ev_sample_003" in ids


def test_invalid_samples_marked_unusable():
    valid = _make_shirt_sample(1, usable=True)
    invalid = _make_shirt_sample(2, usable=False)
    retriever = InMemoryGPMContextRetriever(price_samples=[valid, invalid])
    context = retriever.build_context(requirement=REQUIREMENT)

    usable = [e for e in context.evidence if e.usable_for_analysis]
    unusable = [e for e in context.evidence if not e.usable_for_analysis]
    assert len(usable) == 1
    assert len(unusable) == 1


def test_valid_samples_in_prompt_payload():
    samples = [_make_shirt_sample(i) for i in range(1, 4)]
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(requirement=REQUIREMENT)
    payload = context.to_prompt_payload()
    assert len(payload["evidence"]) == 3
    assert all(e["usable_for_analysis"] for e in payload["evidence"])


def test_limit_parameter_respected():
    samples = [_make_shirt_sample(i) for i in range(1, 11)]
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(requirement=REQUIREMENT, limit=3)
    assert len(context.evidence) == 3


def test_supplier_quote_included():
    samples = [_make_shirt_sample(1)]
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    quote = {"price": "38.5", "currency": "CNY"}
    context = retriever.build_context(requirement=REQUIREMENT, supplier_quote=quote)
    assert context.supplier_quote == quote


def test_data_mode_passed_through():
    samples = [_make_shirt_sample(1)]
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(requirement=REQUIREMENT, data_mode="private")
    assert context.data_mode == "private"
