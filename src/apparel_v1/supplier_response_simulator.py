"""
Mock supplier response simulator for the apparel v1 E2E flow.
Produces three deterministic, scenario-fixed supplier responses:
  - "fast"     → Option A (fastest delivery, higher cost)
  - "cheap"    → Option B (lowest cost, slower delivery)
  - "balanced" → Option C (balanced — recommended)
"""
import uuid
from dataclasses import dataclass, field

from src.apparel_v1.requirement_extractor import ExtractedRequirements


@dataclass
class MockSupplierResponse:
    response_id: str
    supplier_id: str
    supplier_name: str
    profile: str          # "fast", "cheap", or "balanced"
    # Pricing
    unit_price_usd: float
    total_price_usd: float
    currency: str = "USD"
    # Lead time breakdown (days)
    fabric_days: int = 0
    trim_days: int = 0
    production_days: int = 0
    qc_days: int = 0
    packaging_days: int = 0
    logistics_days: int = 0
    supplier_stated_total_days: int = 0
    # Capacity
    daily_capacity_pcs: int = 0
    # Confidence and risk
    risk_flags: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    confidence_score: float = 0.80
    completeness_score: float = 0.80
    # Notes and location
    notes: str = ""
    location: str = "Guangzhou, China"


def simulate_supplier_responses(requirements: ExtractedRequirements) -> list[MockSupplierResponse]:
    """
    Generate mock responses from 3 representative suppliers for the order.

    Profiles:
      fast     — Guangzhou Swift Garment: premium slot, in-house fabric, air-freight capable
      cheap    — Dongguan Value Textile: lowest CM price, third-party fabric, slower turnaround
      balanced — Foshan Reliable Apparel: ISO certified, in-house QC, Japan-export experience
    """
    qty = requirements.quantity or 10000

    # Supplier A — Fast profile
    fast = MockSupplierResponse(
        response_id=f"SRESP-{uuid.uuid4().hex[:8].upper()}",
        supplier_id="SUP-001-FAST",
        supplier_name="Guangzhou Swift Garment Co.",
        profile="fast",
        unit_price_usd=4.20,
        total_price_usd=round(4.20 * qty, 2),
        fabric_days=7,
        trim_days=3,
        production_days=15,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        supplier_stated_total_days=33,
        daily_capacity_pcs=700,
        confidence_score=0.90,
        completeness_score=0.95,
        notes=(
            "Premium-speed production slot available immediately. "
            "In-house 100% cotton fabric stock (180gsm, white & light blue). "
            "Air freight available as back-up. Can start within 2 days of PO receipt."
        ),
        location="Guangzhou, China",
    )

    # Supplier B — Cheap profile
    cheap = MockSupplierResponse(
        response_id=f"SRESP-{uuid.uuid4().hex[:8].upper()}",
        supplier_id="SUP-002-CHEAP",
        supplier_name="Dongguan Value Textile Manufacturing",
        profile="cheap",
        unit_price_usd=3.15,
        total_price_usd=round(3.15 * qty, 2),
        fabric_days=12,
        trim_days=5,
        production_days=20,
        qc_days=2,
        packaging_days=1,
        logistics_days=7,
        supplier_stated_total_days=47,
        daily_capacity_pcs=400,
        confidence_score=0.75,
        completeness_score=0.80,
        risk_flags=[
            "fabric_sourcing_from_third_party",
            "tight_schedule_vs_45d_deadline",
        ],
        notes=(
            "Best market price. Fabric sourced from Zhongshan partner (may add 3-5 days). "
            "Recommend extending buyer deadline to 50 days for margin. "
            "Sea freight only; air freight not offered."
        ),
        location="Dongguan, China",
    )

    # Supplier C — Balanced profile (recommended)
    balanced = MockSupplierResponse(
        response_id=f"SRESP-{uuid.uuid4().hex[:8].upper()}",
        supplier_id="SUP-003-BALANCED",
        supplier_name="Foshan Reliable Apparel Ltd.",
        profile="balanced",
        unit_price_usd=3.65,
        total_price_usd=round(3.65 * qty, 2),
        fabric_days=8,
        trim_days=3,
        production_days=18,
        qc_days=3,
        packaging_days=1,
        logistics_days=6,
        supplier_stated_total_days=39,
        daily_capacity_pcs=550,
        confidence_score=0.88,
        completeness_score=0.92,
        notes=(
            "ISO 9001 certified. OEKO-TEX Standard 100 compliant cotton fabric. "
            "In-house QC team with Japan-export experience. "
            "Payment: 30% deposit, 70% before shipment. "
            "Can accommodate AQL 2.5 with third-party inspector access."
        ),
        location="Foshan, China",
    )

    return [fast, cheap, balanced]
