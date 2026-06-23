from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle


def _sample_to_evidence(sample: Any, index: int) -> GPMEvidenceReference:
    """Convert a GPMSupplierPriceSample-style object or dict into an evidence reference."""
    if isinstance(sample, dict):
        sid = str(sample.get("id", f"sample_{index}"))
        title = sample.get("product_title")
        platform = sample.get("source_platform")
        observed_at = sample.get("observed_at") or sample.get("captured_at")
        usable = sample.get("usable_for_benchmark", True)
        invalid_reasons = sample.get("invalid_reasons", [])
        excerpt: dict = {}
        for key in ("price_min", "price_max", "price_currency", "price_unit", "moq", "moq_unit", "material"):
            val = sample.get(key)
            if val is not None:
                excerpt[key] = str(val)
    else:
        sid = str(getattr(sample, "id", f"sample_{index}"))
        title = getattr(sample, "product_title", None)
        platform = getattr(sample, "source_platform", None)
        observed_at = getattr(sample, "observed_at", None) or getattr(sample, "captured_at", None)
        usable = getattr(sample, "usable_for_benchmark", True)
        invalid_reasons = list(getattr(sample, "invalid_reasons", []))
        excerpt = {}
        for key in ("price_min", "price_max", "price_currency", "price_unit", "moq", "moq_unit", "material"):
            val = getattr(sample, key, None)
            if val is not None:
                excerpt[key] = str(val)

    evidence_id = f"ev_{sid}"

    raw_hash = hashlib.sha256(json.dumps(excerpt, sort_keys=True, default=str).encode()).hexdigest()[:16]

    if isinstance(observed_at, str):
        try:
            observed_at = datetime.fromisoformat(observed_at)
        except ValueError:
            observed_at = None

    return GPMEvidenceReference(
        id=evidence_id,
        source_type="api_sample",
        source_id=sid,
        source_platform=platform,
        title=title,
        observed_at=observed_at,
        payload_excerpt=excerpt if excerpt else None,
        raw_payload_hash=raw_hash,
        usable_for_analysis=bool(usable),
        invalid_reasons=list(invalid_reasons),
    )


class InMemoryGPMContextRetriever:
    """Deterministic in-memory context retriever for MVP tests."""

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
        supplier_quote: dict | None,
        data_mode: str = "mock",
        tenant_id: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
    ) -> GPMContextBundle:
        selected = self._price_samples[:limit]
        evidence = [_sample_to_evidence(s, i) for i, s in enumerate(selected)]

        # Deduplicate evidence IDs (keep first)
        seen: set[str] = set()
        unique_evidence: list[GPMEvidenceReference] = []
        for e in evidence:
            if e.id not in seen:
                seen.add(e.id)
                unique_evidence.append(e)

        price_sample_dicts: list[dict] = []
        for s in selected:
            if isinstance(s, dict):
                price_sample_dicts.append(s)
            else:
                d: dict = {}
                for key in (
                    "id", "product_title", "price_min", "price_max", "price_currency",
                    "price_unit", "moq", "moq_unit", "ladder_prices", "material",
                    "source_platform", "supplier_id", "usable_for_benchmark",
                    "captured_at", "observed_at", "invalid_reasons",
                ):
                    val = getattr(s, key, None)
                    if val is not None:
                        d[key] = val
                price_sample_dicts.append(d)

        return GPMContextBundle(
            bundle_id=f"bundle_{requirement.get('id', 'req')}",
            data_mode=data_mode,  # type: ignore[arg-type]
            tenant_id=tenant_id,
            project_id=project_id,
            requirement=requirement,
            supplier_quote=supplier_quote,
            price_samples=price_sample_dicts,
            supplier_history=self._supplier_history,
            public_market_notes=self._public_market_notes,
            private_order_history=self._private_order_history,
            evidence=unique_evidence,
            created_at=datetime.now(timezone.utc),
        )
