from __future__ import annotations

from typing import Any

from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


class QwenLocalRuntime:
    """Public entry point for GPM code. Routes to the correct Qwen runtime based on config.

    mock    -> MockQwenRuntime (deterministic, CI-safe, no model required)
    mnn     -> QwenMNNRuntime (local model, no network)
    llm_api -> OperatorLLMApiRuntime (operator-selected, disabled by default)

    Never switches modes silently. llm_api raises unless explicitly enabled with a token.
    Backward-compatible: QwenLocalRuntime(mock_mode=True) and QwenLocalRuntime(model_path=...)
    still work via the legacy path.
    """

    def __init__(
        self,
        config: QwenRuntimeConfig | None = None,
        model_path: str | None = None,
        mock_mode: bool = False,
    ) -> None:
        # Legacy callers: resolve from kwargs if no config supplied
        if config is None:
            if mock_mode:
                config = QwenRuntimeConfig(runtime_mode="mock")
            elif model_path is not None:
                config = QwenRuntimeConfig(runtime_mode="mnn", mnn_model_path=model_path)
            else:
                config = QwenRuntimeConfig.from_env()

        self._config = config
        self._runtime = self._build_runtime(config)

    def _build_runtime(self, config: QwenRuntimeConfig) -> Any:
        if config.runtime_mode == "llm_api":
            from src.gpm.qwen.operator_llm_api_runtime import OperatorLLMApiRuntime
            return OperatorLLMApiRuntime(config)

        if config.runtime_mode == "mnn":
            from src.gpm.qwen.qwen_mnn_runtime import QwenMNNRuntime
            return QwenMNNRuntime(config)

        from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
        return MockQwenRuntime()

    @property
    def runtime_mode(self) -> str:
        return self._runtime.runtime_mode

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        return self._runtime.generate_json(prompt, schema_name)
