from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

from src.gpm.models.raw_api_response import GPMRawAPIResponse
from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample
from src.gpm.normalization.sample_validator import validate_sample
from src.gpm.storage.local_json_store import LocalJSONStore


def _make_raw_response() -> GPMRawAPIResponse:
    payload: dict = {"mock": True}
    response_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return GPMRawAPIResponse(
        id="raw_test_001",
        source_platform="1688",
        api_endpoint="https://mock.1688.com/api/offer/search",
        query_keyword="测试衬衫",
        query_payload={"keyword": "测试衬衫"},
        response_payload=payload,
        response_hash=response_hash,
        captured_at=datetime.now(timezone.utc),
        request_status="success",
    )


def _make_sample(raw_id: str) -> GPMSupplierPriceSample:
    now = datetime.now(timezone.utc)
    s = GPMSupplierPriceSample(
        id="sample_store_001",
        source_platform="1688",
        source_offer_id="offer_store_001",
        supplier_id="1688_sup_store_001",
        supplier_name="Store Test Factory",
        supplier_location="Guangzhou, Guangdong",
        captured_at=now,
        observed_at=None,
        product_title="测试衬衫",
        product_url=None,
        image_url=None,
        category_id=None,
        category_name=None,
        material="cotton",
        process_tags=[],
        customization_supported=True,
        price_min=Decimal("30"),
        price_max=Decimal("45"),
        price_currency="CNY",
        price_unit="piece",
        moq=Decimal("500"),
        moq_unit="piece",
        ladder_prices=[{"min_qty": 500, "price": "45"}],
        sku_attributes={},
        delivery_region=None,
        lead_time_text=None,
        raw_response_id=raw_id,
        created_at=now,
    )
    validate_sample(s)
    return s


def test_raw_response_is_saved():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalJSONStore(base_dir=tmpdir)
        raw = _make_raw_response()
        result_id = store.save_raw_response(raw)
        assert result_id == raw.id


def test_response_hash_is_generated():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalJSONStore(base_dir=tmpdir)
        raw = _make_raw_response()
        store.save_raw_response(raw)
        assert raw.response_hash != ""
        assert len(raw.response_hash) == 64  # sha256 hex


def test_price_samples_are_saved():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalJSONStore(base_dir=tmpdir)
        raw = _make_raw_response()
        sample = _make_sample(raw.id)
        ids = store.save_price_samples([sample])
        assert ids == [sample.id]


def test_samples_can_be_loaded_by_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalJSONStore(base_dir=tmpdir)
        raw = _make_raw_response()
        sample = _make_sample(raw.id)
        store.save_price_samples([sample])
        loaded = store.load_price_samples([sample.id])
        assert len(loaded) == 1
        assert loaded[0].id == sample.id
        assert loaded[0].supplier_id == sample.supplier_id
        assert loaded[0].usable_for_benchmark == sample.usable_for_benchmark
        assert loaded[0].invalid_reasons == sample.invalid_reasons
