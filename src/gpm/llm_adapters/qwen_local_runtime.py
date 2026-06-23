from __future__ import annotations

import os
from typing import Any


class QwenLocalRuntime:
    """Local Qwen runtime with deterministic mock mode.

    When mock_mode=True: returns deterministic JSON without any model loading.
    When mock_mode=False: requires a local MNN model; raises RuntimeError if unavailable.
    Never calls DashScope, OpenAI, Anthropic, or any external LLM API.
    """

    def __init__(self, model_path: str | None = None, mock_mode: bool = False) -> None:
        self._mock_mode = mock_mode
        if not mock_mode:
            resolved_path = model_path or os.environ.get("GPM_QWEN_MNN_MODEL_PATH", "").strip()
            if not resolved_path or not os.path.exists(resolved_path):
                raise RuntimeError("Local Qwen/MNN runtime is not available")
            self._model_path = resolved_path
        else:
            self._model_path = None

    @property
    def runtime_mode(self) -> str:
        return "mock" if self._mock_mode else "mnn"

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        if self._mock_mode:
            from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
            return MockQwenRuntime().generate_json(prompt, schema_name)
        # Real MNN inference path — not yet implemented.
        raise RuntimeError("Local Qwen/MNN runtime is not available")
