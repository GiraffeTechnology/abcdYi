"""
Missing information detector for the apparel/textile v1 E2E flow.
Checks extracted requirements against required fields and produces
clarification questions for the buyer.
"""
from dataclasses import dataclass, field

from src.apparel_v1.requirement_extractor import ExtractedRequirements


REQUIRED_FIELDS = [
    "product_type",
    "quantity",
    "fabric_type",
    "color",
    "size_range",
    "delivery_deadline_days",
    "trade_term",
    "destination",
]

FIELD_QUESTION_MAP = {
    "product_type": "What type of apparel product do you need? (e.g., shirt, jacket, trousers)",
    "quantity": "What is the total order quantity in pieces?",
    "fabric_type": "What fabric type do you require? (e.g., 100% cotton, polyester blend)",
    "color": "What colors do you need?",
    "size_range": "What size range do you require? (e.g., S/M/L/XL, EU 38-46)",
    "delivery_deadline_days": "What is your required delivery deadline in days?",
    "trade_term": "What trade term do you prefer? (FOB / CIF / EXW / DDP)",
    "destination": "What is the destination port or delivery address?",
    "qc_standard": "What QC standard should be applied? (default: AQL 2.5)",
    "payment_term": "What are your preferred payment terms? (e.g., 30% deposit, 70% before shipment)",
    "compliance_requirement": "Are there compliance certifications required? (e.g., OEKO-TEX, REACH)",
}


@dataclass
class MissingInfoReport:
    inquiry_id: str
    missing_fields: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    completeness_score: float = 1.0
    is_complete: bool = True


def check_missing_info(requirements: ExtractedRequirements) -> MissingInfoReport:
    """
    Check extracted requirements for missing required fields.
    Returns a MissingInfoReport with per-field clarification questions.
    """
    missing = []
    questions = []

    for field_name in REQUIRED_FIELDS:
        value = getattr(requirements, field_name, None)
        if not value and value != 0:
            missing.append(field_name)
            question = FIELD_QUESTION_MAP.get(field_name, f"Please provide: {field_name}")
            questions.append(question)

    total = len(REQUIRED_FIELDS)
    found = total - len(missing)
    completeness = round(found / total, 2)

    return MissingInfoReport(
        inquiry_id=requirements.inquiry_id,
        missing_fields=missing,
        clarification_questions=questions,
        completeness_score=completeness,
        is_complete=len(missing) == 0,
    )
