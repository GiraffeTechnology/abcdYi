from __future__ import annotations

import os


class QwenMNNRuntime:
    """Local-only Qwen MNN runtime boundary.

    Active only when GPM_QWEN_MNN_MODEL_PATH is set and MNN is installed.
    Does NOT call DashScope, Qwen cloud, or any HTTP LLM API.
    Use MockQwenRuntime for tests.
    """

    runtime_name: str = "qwen_mnn"

    def __init__(
        self,
        model_path: str | None = None,
        tokenizer_path: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        self._model_path = model_path or os.environ.get("GPM_QWEN_MNN_MODEL_PATH")
        self._tokenizer_path = tokenizer_path or os.environ.get("GPM_QWEN_TOKENIZER_PATH")
        self._max_tokens = int(
            os.environ.get("GPM_QWEN_MAX_TOKENS", str(max_tokens))
        )
        self._mnn = None

        if not self._model_path:
            raise RuntimeError(
                "GPM_QWEN_MNN_MODEL_PATH is required for QwenMNNRuntime. "
                "Use MockQwenRuntime for tests."
            )

        try:
            import importlib
            self._mnn = importlib.import_module("MNN")
        except ImportError as exc:
            raise RuntimeError(
                "MNN runtime library is not installed. "
                "QwenMNNRuntime requires a local MNN installation. "
                "Use MockQwenRuntime for tests."
            ) from exc

    def generate_json(
        self, prompt: str, schema_name: str, max_tokens: int = 1024
    ) -> dict:
        if self._mnn is None:
            raise RuntimeError(
                "QwenMNNRuntime is not available: MNN library is not loaded."
            )
        raise NotImplementedError(
            "QwenMNNRuntime.generate_json requires a configured local MNN model. "
            "This is a local-only boundary stub."
        )
