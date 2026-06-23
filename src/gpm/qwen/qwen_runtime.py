from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class QwenRuntime(Protocol):
    """Protocol for local Qwen-style inference runtimes.

    Implementations must:
    - Return parsed JSON dict, not free text.
    - Never call external LLM APIs or cloud services.
    - Be deterministic in tests.
    """

    runtime_name: str

    def generate_json(
        self, prompt: str, schema_name: str, max_tokens: int = 1024
    ) -> dict: ...
