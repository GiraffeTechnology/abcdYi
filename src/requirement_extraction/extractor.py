from src.llm import get_llm_provider
from src.dynamic_forms.constants import STANDARD_FIELDS, FIELD_DESCRIPTIONS, REQUIRED_FIELDS

EXTRACTION_SYSTEM_PROMPT = """
You are an expert apparel & textile procurement specialist.
Extract structured order requirements from buyer inquiry text.
Return ONLY valid JSON. Do not include any preamble or markdown.
All field values must be extracted from the text only.
If a field is not mentioned, set its value to null.
Never invent information.
"""


async def extract_requirements_from_inquiry(raw_text: str) -> dict:
    """
    Call LLM to extract all standard fields from raw buyer inquiry text.
    Returns a dict with field names as keys.
    Fields not found in text are set to null.
    """
    provider = get_llm_provider()

    extractable = [
        f for f in STANDARD_FIELDS
        if f not in ("missing_fields", "clarification_questions")
    ]

    field_list = "\n".join([
        f'  "{f}": "{FIELD_DESCRIPTIONS.get(f, f)}"'
        for f in extractable
    ])

    prompt = f"""
Extract the following fields from this buyer inquiry.
Return as a single JSON object with these exact keys:
{{
{field_list}
}}

Buyer inquiry:
\"\"\"
{raw_text}
\"\"\"
"""
    result = await provider.extract_json(prompt, EXTRACTION_SYSTEM_PROMPT)
    result["_ai_generated"] = True
    return result


def detect_missing_fields(fields: dict) -> list[str]:
    """Return list of REQUIRED_FIELDS that are null or missing."""
    return [
        f for f in REQUIRED_FIELDS
        if not fields.get(f)
    ]


def generate_clarification_questions(fields: dict, missing: list[str]) -> list[str]:
    """Generate clarification questions for missing required fields."""
    questions = []
    for field in missing:
        desc = FIELD_DESCRIPTIONS.get(field, field)
        questions.append(f"Please provide: {desc}")
    return questions
