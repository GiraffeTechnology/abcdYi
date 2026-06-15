import os
from src.llm.provider import LLMProvider
from src.llm.local_stub_provider import LocalStubProvider


def get_llm_provider() -> LLMProvider:
    provider = os.environ.get("LLM_PROVIDER", "stub").lower()
    if provider == "openai":
        from src.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider == "qwen":
        from src.llm.qwen_provider import QwenProvider
        return QwenProvider()
    else:
        return LocalStubProvider()
