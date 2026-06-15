from src.llm.provider import LLMProvider


class LocalStubProvider(LLMProvider):
    """
    Deterministic stub used when no LLM provider is configured.
    All AI-assisted fields are marked _stub=True to signal manual input is required.
    """

    async def complete(self, prompt: str, system: str = "") -> str:
        return "[STUB] No LLM provider configured. Manual input required."

    async def extract_json(self, prompt: str, system: str = "") -> dict:
        return {
            "_stub": True,
            "_message": "No LLM provider configured. Please enter data manually.",
        }
