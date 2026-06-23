from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class QwenRuntime(Protocol):
    runtime_name: str

    def generate_json(self, prompt: str, schema_name: str, max_tokens: int = 1024) -> dict: ...
