"""
Quote generator for the apparel v1 E2E flow.
Produces:
  - QCProcessCard: apparel-specific QC standards and inspection milestone plan
  - BuyerQuote: buyer-facing quotation with all 3 options
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.apparel_v1.requirement_extractor import ExtractedRequirements
from src.apparel_v1.option_generator import BuyerOption


@dataclass
class QCProcessCard:
    card_id: str
    product_type: str
    qc_standard: str
    inspection_milestones: list[dict] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    critical_defects: list[str] = field(default_factory=list)
    major_defects: list[str] = field(default_factory=list)
    minor_defects: list[str] = field(default_factory=list)
    target_market_notes: str = ""


@dataclass
class BuyerQuote:
    quote_id: str
    inquiry_id: str
    generated_at: str
    product_summary: str
    options: list[BuyerOption] = field(default_factory=list)
    recommended_option: Optional[str] = None
    qc_process_card: Optional[QCProcessCard] = None
    human_approval_status: str = "pending"
    validity_days: int = 7
    notes: str = ""


def generate_qc_process_card(requirements: ExtractedRequirements) -> QCProcessCard:
    """
    Generate an apparel-specific QC standard and process card for the order.
    Includes market-specific requirements for Japan.
    """
    product = requirements.product_type or "Shirt"
    standard = requirements.qc_standard or "AQL 2.5"
    market = requirements.target_market or "General"
    qty = requirements.quantity or 10000

    acceptance_criteria = [
        f"AQL 2.5 Level II sampling plan for {qty:,} pieces",
        "Critical defects: ZERO tolerance",
        "Major defects: AQL 2.5 (acceptance number per table)",
        "Minor defects: AQL 4.0",
        "Color: match approved lab-dip ΔE ≤1.0 (CIE L*a*b*)",
        "Measurement: tolerance ±0.5cm in chest, length, sleeve length",
        "Fabric weight: specified GSM ±5%",
        "Stitching density: minimum 12 stitches per 3cm",
        "Seam strength: minimum 100N burst strength",
    ]

    if market == "Japan":
        acceptance_criteria += [
            "Japan: zero stray threads — all thread ends trimmed flush",
            "Japan: individual polybag with anti-moisture silica insert required",
            "Japan: JIS barcode and label compliance mandatory",
            "Japan: care label in Japanese (JIS L 0001) required",
        ]

    critical_defects = [
        "Wrong fabric composition (non-spec material)",
        "Wrong color (completely different hue to approved shade card)",
        "Size entirely wrong (>2cm deviation from size spec)",
        "Structural failure: burst seam, fabric hole, broken stitch >5cm",
        "Prohibited substance violation (REACH / OEKO-TEX)",
        "Incorrect or missing country of origin label",
        "Wrong product (different style delivered)",
    ]

    major_defects = [
        "Color variation within shipment ΔE > 1.0",
        "Measurement deviation > 0.5cm in critical dimensions",
        "Stitching skip: > 1 skip per 3cm",
        "Incorrect care instruction label or missing label",
        "Trim missing, wrong specification, or loose attachment",
        "Packing not per buyer specification",
        "Running stitch visible on finished face",
    ]

    minor_defects = [
        "Minor removable stain < 5mm diameter",
        "Thread trimming not perfectly clean (< 3mm stray thread)",
        "Minor pressing crease on non-visible area",
        "Carton marking minor error on non-critical field",
    ]

    inspection_milestones = [
        {
            "stage": "Fabric Receipt Inspection",
            "timing": "Before cutting (Day 0 of cutting)",
            "check_points": [
                "Fabric weight (GSM per square meter)",
                "Color match vs approved lab-dip (ΔE reading)",
                "Fabric width at intervals",
                "Defects per 100m² (4-point system)",
                "Shrinkage test (wash and dry)",
            ],
            "pass_criteria": "≤10 defects/100m², GSM ±5%, ΔE ≤1.0, shrinkage <3%",
        },
        {
            "stage": "Cutting QC",
            "timing": "Day 1 of cutting",
            "check_points": [
                "Lay plan accuracy vs approved marker",
                "Marker efficiency ≥85%",
                "Size label accuracy in bundles",
                "Blade sharpness check",
                "First cut measurement vs size spec",
            ],
            "pass_criteria": "Zero mis-cuts, measurements within ±0.3cm, correct bundle labels",
        },
        {
            "stage": "Inline Inspection (50% production)",
            "timing": "When 50% of production is sewn",
            "check_points": [
                "Stitching quality (SPI, seam type, tension)",
                "Seam strength test (burst, tensile)",
                "Trim attachment (buttons, zippers, labels)",
                "Pressing and finishing quality",
                "Measurement check (chest, length, sleeve)",
            ],
            "pass_criteria": "AQL 2.5, zero critical, major ≤2.5%, action plan if fail",
        },
        {
            "stage": "Final QC Inspection",
            "timing": "100% production complete, before packing",
            "check_points": [
                "Full AQL 2.5 Level II visual inspection",
                "Measurement (all critical dimensions per size spec)",
                "Trims: buttons, zippers, labels, tags",
                "Labels: brand, care, size, country of origin",
                "Packing: polybag, folding, sticker",
            ],
            "pass_criteria": "AQL 2.5 Level II — critical 0%, major 2.5%, minor 4.0%",
        },
        {
            "stage": "Pre-Shipment Inspection",
            "timing": "Before container loading",
            "check_points": [
                "Carton count vs packing list",
                "Random carton opening (20% of cartons)",
                "Barcode scan and label accuracy",
                "Outer carton marking: style, size, qty, shipper, consignee",
                "Gross weight and measurement per carton",
            ],
            "pass_criteria": "100% carton count match, zero label errors, dimensions within ±2cm",
        },
    ]

    return QCProcessCard(
        card_id=f"QC-CARD-{uuid.uuid4().hex[:8].upper()}",
        product_type=product,
        qc_standard=standard,
        inspection_milestones=inspection_milestones,
        acceptance_criteria=acceptance_criteria,
        critical_defects=critical_defects,
        major_defects=major_defects,
        minor_defects=minor_defects,
        target_market_notes=(
            f"Target market: {market}. "
            + ("Apply Japan-specific standards as itemised in acceptance criteria above." if market == "Japan"
               else "Apply standard export QC requirements.")
        ),
    )


def generate_buyer_quote(
    requirements: ExtractedRequirements,
    options: list[BuyerOption],
    qc_process_card: QCProcessCard,
    human_approved: bool = False,
) -> BuyerQuote:
    """
    Generate the buyer-facing quotation document with all 3 options.
    Sets human_approval_status on the quote and all options.
    """
    # Option C (balanced) is the recommended choice
    recommended = next((o.option_label for o in options if o.option_label == "C"), None)
    if recommended is None and options:
        recommended = options[0].option_label

    approval_status = "approved" if human_approved else "pending"
    for opt in options:
        opt.human_approval_status = approval_status

    product_summary = (
        f"{requirements.quantity or 10000:,} pcs "
        f"{requirements.product_type or 'Cotton Shirt'} "
        f"({requirements.color or 'White/Light Blue'}), "
        f"sizes {requirements.size_range or 'S/M/L/XL'}, "
        f"{requirements.fabric_type or '100% cotton'}, "
        f"{requirements.trade_term or 'FOB'} within "
        f"{requirements.delivery_deadline_days or 45} days"
    )

    return BuyerQuote(
        quote_id=f"QUOTE-{uuid.uuid4().hex[:8].upper()}",
        inquiry_id=requirements.inquiry_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        product_summary=product_summary,
        options=options,
        recommended_option=recommended,
        qc_process_card=qc_process_card,
        human_approval_status=approval_status,
        validity_days=7,
        notes=(
            f"All prices in USD, {requirements.trade_term or 'FOB'} China. "
            f"QC standard: {qc_process_card.qc_standard}. "
            "Subject to final inspection and buyer written approval. "
            "Quote validity: 7 days from issuance."
        ),
    )
