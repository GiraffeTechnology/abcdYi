import pytest
from src.requirement_extraction.extractor import (
    extract_requirements_from_inquiry,
    detect_missing_fields,
    generate_clarification_questions,
)


@pytest.mark.asyncio
async def test_stub_extraction_marks_ai_generated():
    """With stub provider, result must be marked _ai_generated."""
    result = await extract_requirements_from_inquiry("We need shirts.")
    assert result.get("_ai_generated") is True


def test_detect_missing_required_fields():
    fields = {"product_type": "T-shirt", "quantity": None, "color": "White"}
    missing = detect_missing_fields(fields)
    assert "quantity" in missing


def test_generate_clarification_questions():
    missing = ["quantity", "delivery_deadline"]
    questions = generate_clarification_questions({}, missing)
    assert len(questions) == 2
