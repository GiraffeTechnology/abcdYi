from __future__ import annotations

import os


def get_qwen_runtime() -> object:
    """Resolve and return the configured Qwen runtime.

    GPM_QWEN_RUNTIME=mock (default) | mnn
    """
    runtime_mode = os.environ.get("GPM_QWEN_RUNTIME", "mock").lower().strip()

    if runtime_mode == "mnn":
        from src.gpm.qwen.qwen_mnn_runtime import QwenMNNRuntime
        return QwenMNNRuntime()

    # Default: deterministic mock runtime safe for tests
    from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
    return MockQwenRuntime()
