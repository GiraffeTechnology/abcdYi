from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.gpm.models.raw_api_response import GPMRawAPIResponse
from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample


def _json_default(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _parse_sample(data: dict) -> GPMSupplierPriceSample:
    def _dt(v: str | None) -> datetime | None:
        return datetime.fromisoformat(v) if v else None

    def _dec(v: str | None) -> Decimal | None:
        return Decimal(v) if v is not None else None

    sample = GPMSupplierPriceSample(
        id=data["id"],
        source_platform=data["source_platform"],
        source_offer_id=data.get("source_offer_id"),
        supplier_id=data.get("supplier_id"),
        supplier_name=data.get("supplier_name"),
        supplier_location=data.get("supplier_location"),
        captured_at=_dt(data.get("captured_at")),
        observed_at=_dt(data.get("observed_at")),
        product_title=data["product_title"],
        product_url=data.get("product_url"),
        image_url=data.get("image_url"),
        category_id=data.get("category_id"),
        category_name=data.get("category_name"),
        material=data.get("material"),
        process_tags=data.get("process_tags", []),
        customization_supported=data.get("customization_supported"),
        price_min=_dec(data.get("price_min")),
        price_max=_dec(data.get("price_max")),
        price_currency=data.get("price_currency", "CNY"),
        price_unit=data.get("price_unit", "piece"),
        moq=_dec(data.get("moq")),
        moq_unit=data.get("moq_unit"),
        ladder_prices=data.get("ladder_prices", []),
        sku_attributes=data.get("sku_attributes", {}),
        delivery_region=data.get("delivery_region"),
        lead_time_text=data.get("lead_time_text"),
        raw_response_id=data["raw_response_id"],
        created_at=_dt(data.get("created_at")) or datetime.now(),
    )
    sample.usable_for_benchmark = data.get("usable_for_benchmark", False)
    sample.usable_for_quote_guidance = data.get("usable_for_quote_guidance", False)
    sample.invalid_reasons = data.get("invalid_reasons", [])
    return sample


class LocalJSONStore:
    def __init__(self, base_dir: str = "data/gpm") -> None:
        self._raw_dir = Path(base_dir) / "raw_api_responses"
        self._sample_dir = Path(base_dir) / "supplier_price_samples"
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._sample_dir.mkdir(parents=True, exist_ok=True)

    def save_raw_response(self, response: GPMRawAPIResponse) -> str:
        path = self._raw_dir / f"{response.id}.json"
        data = {
            "id": response.id,
            "source_platform": response.source_platform,
            "api_endpoint": response.api_endpoint,
            "query_keyword": response.query_keyword,
            "query_payload": response.query_payload,
            "response_payload": response.response_payload,
            "response_hash": response.response_hash,
            "captured_at": response.captured_at.isoformat(),
            "api_account_id": response.api_account_id,
            "request_status": response.request_status,
            "error_message": response.error_message,
        }
        path.write_text(json.dumps(data, indent=2, default=_json_default), encoding="utf-8")
        return response.id

    def save_price_samples(self, samples: list[GPMSupplierPriceSample]) -> list[str]:
        ids: list[str] = []
        for sample in samples:
            path = self._sample_dir / f"{sample.id}.json"
            data = {
                "id": sample.id,
                "source_platform": sample.source_platform,
                "source_offer_id": sample.source_offer_id,
                "supplier_id": sample.supplier_id,
                "supplier_name": sample.supplier_name,
                "supplier_location": sample.supplier_location,
                "captured_at": sample.captured_at.isoformat() if sample.captured_at else None,
                "observed_at": sample.observed_at.isoformat() if sample.observed_at else None,
                "product_title": sample.product_title,
                "product_url": sample.product_url,
                "image_url": sample.image_url,
                "category_id": sample.category_id,
                "category_name": sample.category_name,
                "material": sample.material,
                "process_tags": sample.process_tags,
                "customization_supported": sample.customization_supported,
                "price_min": str(sample.price_min) if sample.price_min is not None else None,
                "price_max": str(sample.price_max) if sample.price_max is not None else None,
                "price_currency": sample.price_currency,
                "price_unit": sample.price_unit,
                "moq": str(sample.moq) if sample.moq is not None else None,
                "moq_unit": sample.moq_unit,
                "ladder_prices": sample.ladder_prices,
                "sku_attributes": sample.sku_attributes,
                "delivery_region": sample.delivery_region,
                "lead_time_text": sample.lead_time_text,
                "raw_response_id": sample.raw_response_id,
                "usable_for_benchmark": sample.usable_for_benchmark,
                "usable_for_quote_guidance": sample.usable_for_quote_guidance,
                "invalid_reasons": sample.invalid_reasons,
                "created_at": sample.created_at.isoformat() if sample.created_at else None,
            }
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            ids.append(sample.id)
        return ids

    def load_price_samples(self, ids: list[str]) -> list[GPMSupplierPriceSample]:
        samples: list[GPMSupplierPriceSample] = []
        for sid in ids:
            path = self._sample_dir / f"{sid}.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            samples.append(_parse_sample(data))
        return samples
