from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


class QwenMNNRuntime:
    """Local MNN-backed Qwen runtime. Only usable when MNN model files are present.

    No network calls. No cloud fallback. Raises clearly when model path is missing.
    """

    runtime_mode = "mnn"

    def __init__(self, config: "QwenRuntimeConfig | None" = None) -> None:
        if config is None:
            from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
            config = QwenRuntimeConfig.from_env()

        model_path = config.mnn_model_path or os.environ.get("GPM_QWEN_MNN_MODEL_PATH", "").strip()
        tokenizer_path = config.mnn_tokenizer_path or os.environ.get("GPM_QWEN_TOKENIZER_PATH", "").strip()

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
        self._config = config
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

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        # Real MNN inference is not yet implemented — stub raises to prevent silent fallback.
        raise NotImplementedError(
            "QwenMNNRuntime.generate_json() is not yet implemented. "
            "Use MockQwenRuntime for tests or implement MNN inference calls here."
        )
