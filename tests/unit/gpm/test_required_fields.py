from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample
from src.gpm.normalization.sample_validator import validate_sample


def _make_valid_sample(**overrides) -> GPMSupplierPriceSample:
    now = datetime.now(timezone.utc)
    defaults: dict = dict(
        id="test_sample_001",
        source_platform="1688",
        source_offer_id="offer_001",
        supplier_id="1688_sup_001",
        supplier_name="Test Factory",
        supplier_location="Guangzhou, Guangdong",
        captured_at=now,
        observed_at=None,
        product_title="男士纯棉衬衫",
        product_url=None,
        image_url=None,
        category_id=None,
        category_name=None,
        material="cotton",
        process_tags=[],
        customization_supported=True,
        price_min=Decimal("28"),
        price_max=Decimal("45"),
        price_currency="CNY",
        price_unit="piece",
        moq=Decimal("500"),
        moq_unit="piece",
        ladder_prices=[{"min_qty": 500, "price": "45"}],
        sku_attributes={},
        delivery_region=None,
        lead_time_text=None,
        raw_response_id="raw_001",
        created_at=now,
    )
    defaults.update(overrides)
    return GPMSupplierPriceSample(**defaults)


def test_missing_supplier_id_excludes_sample():
    sample = _make_valid_sample(supplier_id=None)
    validate_sample(sample)
    assert not sample.usable_for_benchmark
    assert "missing_supplier_id" in sample.invalid_reasons


def test_missing_moq_excludes_sample():
    sample = _make_valid_sample(moq=None)
    validate_sample(sample)
    assert not sample.usable_for_benchmark
    assert "missing_moq" in sample.invalid_reasons


def test_missing_observed_time_excludes_sample():
    sample = _make_valid_sample(captured_at=None, observed_at=None)
    validate_sample(sample)
    assert not sample.usable_for_benchmark
    assert "missing_observed_time" in sample.invalid_reasons


def test_missing_price_excludes_sample():
    sample = _make_valid_sample(price_min=None, ladder_prices=[])
    validate_sample(sample)
    assert not sample.usable_for_benchmark
    assert "missing_price" in sample.invalid_reasons


def test_valid_sample_is_benchmark_eligible():
    sample = _make_valid_sample()
    validate_sample(sample)
    assert sample.usable_for_benchmark
    assert sample.usable_for_quote_guidance
    assert sample.invalid_reasons == []
