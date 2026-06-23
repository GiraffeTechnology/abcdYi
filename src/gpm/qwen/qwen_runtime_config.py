from __future__ import annotations

import os


def get_qwen_runtime():
    """Resolve the active Qwen runtime from environment.

    GPM_QWEN_RUNTIME=mock | mnn
    Defaults to 'mock' for all tests and offline environments.
    """
    runtime_name = os.environ.get("GPM_QWEN_RUNTIME", "mock").lower().strip()

    if runtime_name == "mock":
        from .mock_qwen_runtime import MockQwenRuntime
        return MockQwenRuntime()
    elif runtime_name == "mnn":
        from .qwen_mnn_runtime import QwenMNNRuntime
        return QwenMNNRuntime()
    else:
        raise ValueError(
            f"Unknown GPM_QWEN_RUNTIME value: {runtime_name!r}. "
            "Supported values: 'mock', 'mnn'."
        )
