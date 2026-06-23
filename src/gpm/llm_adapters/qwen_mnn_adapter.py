from __future__ import annotations

from .local_llm_adapter import LocalLLMAdapter


class QwenMNNAdapter(LocalLLMAdapter):
    """
    Stub adapter for a locally-deployed Qwen model via MNN runtime.

    Never calls Qwen cloud API, DashScope, or any external LLM endpoint.
    Raises RuntimeError when the local MNN runtime is not configured.
    """

    def __init__(self, model_path: str | None = None) -> None:
        self._model_path = model_path
        self._runtime_available = False

        if model_path:
            try:
                import importlib
                mnn = importlib.import_module("MNN")
                if mnn is not None:
                    self._runtime_available = True
            except ImportError:
                self._runtime_available = False

    def normalize_price_sample(self, requirement: dict, sample: object) -> dict:
        if not self._runtime_available:
            raise RuntimeError(
                "Qwen-MNN runtime is not configured. Use MockLLMAdapter for tests."
            )
        raise NotImplementedError(
            "QwenMNNAdapter.normalize_price_sample requires a configured MNN runtime."
        )
