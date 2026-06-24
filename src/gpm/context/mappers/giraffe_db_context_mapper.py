"""Maps giraffe-db GPMContextResponse dicts to GPMContextBundle."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle

_CREDENTIAL_KEYS = frozenset({
    # Base set
    "password", "passwd", "token", "api_key", "apikey", "secret",
    "authorization", "cookie", "session", "private_key", "access_key",
    "auth", "bearer", "credential",
    # Extended variants
    "access_token", "refresh_token", "api_token", "authorization_header",
    "id_token", "client_secret", "jwt", "x_api_key",
})


class InsufficientContextDataError(ValueError):
    """Raised when giraffe-db returns no usable evidence or price samples."""


def _strip_credentials(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: _strip_credentials(v) for k, v in d.items() if k.lower() not in _CREDENTIAL_KEYS}
    if isinstance(d, list):
        return [_strip_credentials(item) for item in d]
    return d


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


class GiraffeDBContextMapper:
    """Maps a giraffe-db GPMContextResponse dict to a GPMContextBundle."""

    def map(self, response: dict, include_private_data: bool = False) -> GPMContextBundle:
        pricing_context = response.get("pricing_context") or {}
        bundle_id = response.get("id") or str(uuid.uuid4())
        tenant_id = response.get("tenant_id")
        project_id = response.get("project_id")
        created_at = _parse_datetime(response.get("created_at")) or datetime.now(timezone.utc)

        rfq = pricing_context.get("rfq") or {}
        requirement = _strip_credentials(dict(rfq)) if rfq else {}

        supplier_quote_raw = pricing_context.get("supplier_quote")
        supplier_quote: dict | None = None
        if supplier_quote_raw:
            sq = _strip_credentials(dict(supplier_quote_raw))
            for k in ("unit_price", "moq"):
                if k in sq and sq[k] is not None:
                    d = _to_decimal(sq[k])
                    if d is not None:
                        sq[k] = d
            supplier_quote = sq

        evidence_seen: set[str] = set()
        evidence: list[GPMEvidenceReference] = []
        price_samples: list[dict] = []
        price_sample_ids: set[str] = set()
        has_private = False

        def _add_evidence(ref: GPMEvidenceReference) -> None:
            if ref.id not in evidence_seen:
                evidence_seen.add(ref.id)
                evidence.append(ref)

        def _add_price_sample(item_id: str, sample: dict) -> None:
            if item_id not in price_sample_ids:
                price_sample_ids.add(item_id)
                price_samples.append(sample)

        # pricing_evidence → evidence + price_samples
        for item in pricing_context.get("pricing_evidence") or []:
            ref, sample = self._map_evidence_item(item)
            _add_evidence(ref)
            _add_price_sample(ref.id, sample)

        # imported_api_records → evidence + price_samples
        for item in pricing_context.get("imported_api_records") or []:
            ref, sample = self._map_evidence_item(item)
            _add_evidence(ref)
            _add_price_sample(ref.id, sample)

        # public_benchmark_sample is alias for imported_api_records — dedup handles overlap
        for item in pricing_context.get("public_benchmark_sample") or []:
            ref, sample = self._map_evidence_item(item)
            _add_evidence(ref)
            _add_price_sample(ref.id, sample)

        # supplier_response_packets → evidence only
        for item in pricing_context.get("supplier_response_packets") or []:
            ref = self._map_record_evidence(item, fallback_source_type="supplier_response")
            _add_evidence(ref)

        # system_generated_records → evidence
        for item in pricing_context.get("system_generated_records") or []:
            ref = self._map_record_evidence(item, fallback_source_type="system_internal")
            _add_evidence(ref)

        # private data: evidence only, only when include_private_data=True
        if include_private_data:
            for item in pricing_context.get("private_data_records") or []:
                ref = self._map_record_evidence(item, fallback_source_type="private_order")
                _add_evidence(ref)
                has_private = True

            # private_customer_quote_history is alias — dedup handles overlap
            for item in pricing_context.get("private_customer_quote_history") or []:
                ref = self._map_record_evidence(item, fallback_source_type="private_quote_history")
                _add_evidence(ref)
                has_private = True

        if not evidence and not price_samples:
            raise InsufficientContextDataError(
                f"giraffe-db context {bundle_id!r} returned no usable evidence or price samples"
            )

        if has_private and price_samples:
            data_mode = "mixed"
        elif has_private:
            data_mode = "private"
        else:
            data_mode = "public"

        return GPMContextBundle(
            bundle_id=bundle_id,
            data_mode=data_mode,  # type: ignore[arg-type]
            requirement=requirement,
            evidence=evidence,
            tenant_id=tenant_id,
            project_id=project_id,
            supplier_quote=supplier_quote,
            price_samples=price_samples,
            supplier_history=[],
            public_market_notes=[],
            private_order_history=[],
            created_at=created_at,
        )

    def _map_evidence_item(self, item: dict) -> tuple[GPMEvidenceReference, dict]:
        item_id = item.get("id") or str(uuid.uuid4())
        payload = _strip_credentials(item.get("payload") or {})
        source_platform = item.get("source_platform") or payload.get("source_platform", "unknown")
        raw_payload_hash = item.get("raw_payload_hash")

        ref = GPMEvidenceReference(
            id=item_id,
            source_type=item.get("source_type", "pricing_evidence"),
            source_id=item.get("source_id") or item_id,
            source_platform=source_platform,
            title=payload.get("product_title"),
            observed_at=_parse_datetime(item.get("created_at") or payload.get("captured_at")),
            payload_excerpt=payload,
            raw_payload_hash=raw_payload_hash,
            usable_for_analysis=item.get("usable_for_benchmark", True),
            invalid_reasons=item.get("invalid_reasons") or [],
        )

        sample = {
            "id": item_id,
            "product_title": payload.get("product_title", ""),
            "price_min": _to_decimal(payload.get("price_min")),
            "price_max": _to_decimal(payload.get("price_max")),
            "price_currency": payload.get("price_currency", "CNY"),
            "price_unit": payload.get("price_unit", "piece"),
            "moq": _to_decimal(payload.get("moq")),
            "moq_unit": payload.get("moq_unit", "piece"),
            "material": payload.get("material", ""),
            "source_platform": source_platform,
            "usable_for_benchmark": item.get("usable_for_benchmark", True),
            "invalid_reasons": item.get("invalid_reasons") or [],
            "ladder_prices": payload.get("ladder_prices") or [],
        }

        return ref, sample

    def _map_record_evidence(self, item: dict, fallback_source_type: str) -> GPMEvidenceReference:
        item_id = item.get("id") or str(uuid.uuid4())
        payload = _strip_credentials(item.get("payload") or {})
        source_platform = item.get("source_platform") or payload.get("source_platform", "unknown")
        raw_payload_hash = item.get("raw_payload_hash")

        return GPMEvidenceReference(
            id=item_id,
            source_type=item.get("source_type") or fallback_source_type,
            source_id=item.get("source_id") or item_id,
            source_platform=source_platform,
            title=payload.get("title") or payload.get("product_title"),
            observed_at=_parse_datetime(
                item.get("created_at") or payload.get("captured_at") or payload.get("created_at")
            ),
            payload_excerpt=payload,
            raw_payload_hash=raw_payload_hash,
            usable_for_analysis=item.get("usable_for_analysis", True),
            invalid_reasons=item.get("invalid_reasons") or [],
        )
