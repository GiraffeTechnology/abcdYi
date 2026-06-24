from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever

# Canonical 10,000 men's cotton shirt scenario
# Prices 24.0 → 46.04 (step ~1.16) give benchmark:
#   P50 ≈ 35.02, P75 ≈ 40.53
#   (P50 + P75)/2 ≈ 37.78  < 38.5 → within_high_range → negotiate
_CANONICAL_PRICES = [Decimal(str(round(24.0 + i * 1.16, 2))) for i in range(20)]

_CANONICAL_TITLES = [
    "men cotton shirt OEM custom Japan export",
    "100% cotton shirt men OEM",
    "OEM cotton shirt men Japan",
    "men shirt 100% cotton custom",
    "pure cotton shirt OEM Japan",
    "men cotton shirt wholesale OEM",
    "100% cotton OEM shirt Japan export",
    "men shirt cotton fabric OEM custom",
    "cotton shirt custom men Japan",
    "men OEM cotton shirt Japan export",
    "cotton shirt men manufacturing OEM",
    "men cotton shirt bulk order Japan",
    "100% cotton shirt OEM bulk",
    "OEM men shirt cotton Japan",
    "men shirt pure cotton OEM custom",
    "men cotton shirt custom order Japan",
    "pure cotton OEM shirt export",
    "men shirt cotton wholesale Japan",
    "custom men shirt 100% cotton OEM",
    "men cotton shirt factory OEM Japan",
]

CANONICAL_REQUIREMENT = {
    "id": "req-mock-canonical-001",
    "product": "men's cotton shirt",
    "quantity": 10000,
    "unit": "piece",
    "material": "100% cotton",
    "process_tags": ["cutting", "sewing", "buttoning", "packing"],
    "target_market": "Japan",
    "source_platform": "mock_1688",
}

CANONICAL_SUPPLIER_QUOTE = {
    "supplier_id": "supplier_canonical_abc",
    "unit_price": 38.5,
    "currency": "CNY",
    "unit": "piece",
    "moq": 1000,
}


@dataclass
class _CanonicalSample:
    id: str
    product_title: str
    price_min: Decimal
    # price_max intentionally omitted so PriceNormalizer uses price_min directly,
    # keeping the benchmark range predictable for the canonical scenario.
    price_max: Decimal | None = None
    price_currency: str = "CNY"
    price_unit: str = "piece"
    moq: Decimal = Decimal("1000")
    moq_unit: str = "piece"
    material: str = "100% cotton"
    source_platform: str = "mock_1688"
    usable_for_benchmark: bool = True
    invalid_reasons: list[str] = field(default_factory=list)
    ladder_prices: list[dict] = field(default_factory=list)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _make_canonical_samples() -> list[_CanonicalSample]:
    return [
        _CanonicalSample(
            id=f"canonical-{i+1:03d}",
            product_title=_CANONICAL_TITLES[i],
            price_min=_CANONICAL_PRICES[i],
            ladder_prices=[],
        )
        for i in range(20)
    ]


class MockContextRetriever:
    """Deterministic retriever for the canonical 10,000 men's cotton shirt GPM scenario."""

    def retrieve(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool | None = None,
        evidence_ids: list[str] | None = None,
    ) -> GPMContextBundle:
        """Session E primary interface. evidence_ids and include_private_data ignored in mock mode."""
        return self.build_gpm_context(
            tenant_id=tenant_id,
            project_id=project_id,
            rfq_id=rfq_id,
            supplier_response_id=supplier_response_id,
            include_private_data=bool(include_private_data),
        )

    def build_gpm_context(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool = False,
    ) -> GPMContextBundle:
        samples = _make_canonical_samples()
        retriever = InMemoryGPMContextRetriever(price_samples=samples)
        return retriever.build_context(
            requirement=CANONICAL_REQUIREMENT,
            supplier_quote=CANONICAL_SUPPLIER_QUOTE,
            data_mode="mock",
            tenant_id=tenant_id,
            project_id=project_id,
            limit=20,
        )
