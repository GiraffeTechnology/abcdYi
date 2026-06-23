from __future__ import annotations

import json
import os


class QwenMNNRuntime:
    """Local MNN-backed Qwen runtime. Only usable when MNN model files are present."""

    runtime_name = "qwen_mnn"

    def __init__(self) -> None:
        model_path = os.environ.get("GPM_QWEN_MNN_MODEL_PATH", "")
        tokenizer_path = os.environ.get("GPM_QWEN_TOKENIZER_PATH", "")
        self._max_tokens = int(os.environ.get("GPM_QWEN_MAX_TOKENS", "1024"))

        if not model_path:
            raise RuntimeError(
                "GPM_QWEN_MNN_MODEL_PATH is required for local Qwen MNN runtime. "
                "Set this environment variable to the path of your local .mnn model file. "
                "Do not use Qwen cloud or DashScope — this is a local-only runtime."
            )
        if not os.path.exists(model_path):
            raise RuntimeError(
                f"GPM_QWEN_MNN_MODEL_PATH={model_path!r} does not exist. "
                "Ensure the local MNN model file is present."
            )

        self._model_path = model_path
        self._tokenizer_path = tokenizer_path
        self._model = self._load_model()

    def _load_model(self) -> object:
        try:
            import MNN  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "MNN Python package is not installed. "
                "Install it from the MNN project for local inference. "
                "Do not use cloud APIs as a fallback."
            ) from exc
        return MNN

    def generate_json(self, prompt: str, schema_name: str, max_tokens: int = 1024) -> dict:
        # Real implementation calls the local MNN model.
        # Not implemented here — the stub raises to prevent silent cloud fallback.
        raise NotImplementedError(
            "QwenMNNRuntime.generate_json() is not yet implemented. "
            "Use MockQwenRuntime for tests or implement MNN inference calls here."
        )
