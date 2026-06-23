from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class QwenRuntime(Protocol):
    runtime_mode: str

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]: ...
