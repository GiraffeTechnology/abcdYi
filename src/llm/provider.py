from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> str:
        """Return LLM text completion."""
        ...

    @abstractmethod
    async def extract_json(self, prompt: str, system: str = "") -> dict[str, Any]:
        """Return structured JSON extraction."""
        ...
