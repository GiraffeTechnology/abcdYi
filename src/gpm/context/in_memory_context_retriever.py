from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .evidence_reference import GPMEvidenceReference
from .gpm_context_bundle import GPMContextBundle

_SAFE_ATTRS = [
    "id", "product_title", "source_platform", "source_offer_id",
    "supplier_id", "supplier_name", "supplier_location",
    "material", "process_tags", "category_name",
    "price_min", "price_max", "price_currency", "price_unit",
    "moq", "moq_unit", "customization_supported",
    "delivery_region", "lead_time_text",
]


class InMemoryGPMContextRetriever:
    """Deterministic in-memory context retriever for MVP and tests.

    Accepts Session A GPMSupplierPriceSample-style objects or plain dicts.
    Does not require database access.
    """

    def __init__(
        self,
        price_samples: list[Any],
        supplier_history: list[dict] | None = None,
        public_market_notes: list[dict] | None = None,
        private_order_history: list[dict] | None = None,
    ) -> None:
        self._price_samples = price_samples
        self._supplier_history = supplier_history or []
        self._public_market_notes = public_market_notes or []
        self._private_order_history = private_order_history or []

    def build_context(
        self,
        requirement: dict,
        supplier_quote: dict | None = None,
        data_mode: str = "mock",
        tenant_id: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
    ) -> GPMContextBundle:
        evidence: list[GPMEvidenceReference] = []
        price_sample_dicts: list[dict] = []

        for sample in self._price_samples[:limit]:
            raw_id = getattr(sample, "id", None) or (
                sample.get("id") if isinstance(sample, dict) else str(id(sample))
            )
            ev_id = f"ev_{raw_id}"

            excerpt = _build_excerpt(sample)

            usable = True
            invalid_reasons: list[str] = []

            if hasattr(sample, "usable_for_benchmark"):
                usable = bool(sample.usable_for_benchmark)
            elif isinstance(sample, dict):
                usable = sample.get("usable_for_benchmark", True)

            if hasattr(sample, "invalid_reasons") and sample.invalid_reasons:
                invalid_reasons = list(sample.invalid_reasons)
                usable = False
            elif isinstance(sample, dict) and sample.get("invalid_reasons"):
                invalid_reasons = list(sample["invalid_reasons"])
                usable = False

            ref = GPMEvidenceReference(
                id=ev_id,
                source_type="api_sample",
                source_id=str(raw_id),
                source_platform=getattr(sample, "source_platform", None)
                    or (sample.get("source_platform") if isinstance(sample, dict) else None),
                title=getattr(sample, "product_title", None)
                    or (sample.get("product_title") if isinstance(sample, dict) else None),
                observed_at=getattr(sample, "observed_at", None)
                    or (sample.get("observed_at") if isinstance(sample, dict) else None),
                payload_excerpt=excerpt,
                raw_payload_hash=_hash_excerpt(excerpt),
                usable_for_analysis=usable,
                invalid_reasons=invalid_reasons,
            )
            evidence.append(ref)
            price_sample_dicts.append({"evidence_id": ev_id, **excerpt})

        return GPMContextBundle(
            bundle_id=str(uuid.uuid4()),
            data_mode=data_mode,  # type: ignore[arg-type]
            requirement=requirement,
            supplier_quote=supplier_quote,
            price_samples=price_sample_dicts,
            supplier_history=self._supplier_history,
            public_market_notes=self._public_market_notes,
            private_order_history=self._private_order_history,
            evidence=evidence,
            tenant_id=tenant_id,
            project_id=project_id,
            created_at=datetime.now(timezone.utc),
        )


def _build_excerpt(sample: Any) -> dict:
    excerpt: dict = {}
    for attr in _SAFE_ATTRS:
        if isinstance(sample, dict):
            val = sample.get(attr)
        else:
            val = getattr(sample, attr, None)
        if val is not None:
            if val.__class__.__name__ == "Decimal":
                excerpt[attr] = str(val)
            else:
                excerpt[attr] = val
    return excerpt


def _hash_excerpt(excerpt: dict) -> str:
    raw = json.dumps(excerpt, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
