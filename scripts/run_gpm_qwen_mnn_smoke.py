"""GPM Qwen MNN smoke test: check local MNN runtime availability."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, ".")


def main() -> None:
    enabled = os.environ.get("GPM_ENABLE_LIVE_QWEN_MNN_TESTS", "0").strip() == "1"

    if not enabled:
        print("GPM QWEN MNN SMOKE: SKIPPED")
        print("reason: set GPM_ENABLE_LIVE_QWEN_MNN_TESTS=1 to enable live local runtime check")
        return

    model_path = os.environ.get("GPM_QWEN_MNN_MODEL_PATH", "").strip()
    if not model_path:
        print("GPM QWEN MNN SMOKE: FAIL")
        print("reason: GPM_QWEN_MNN_MODEL_PATH is required")
        sys.exit(1)

    if not os.path.exists(model_path):
        print("GPM QWEN MNN SMOKE: FAIL")
        print(f"reason: GPM_QWEN_MNN_MODEL_PATH={model_path!r} does not exist")
        sys.exit(1)

    try:
        from src.gpm.qwen.qwen_mnn_runtime import QwenMNNRuntime
        runtime = QwenMNNRuntime()
        print("GPM QWEN MNN SMOKE: PASS")
        print(f"runtime: {runtime.runtime_name}")
    except RuntimeError as e:
        print("GPM QWEN MNN SMOKE: FAIL")
        print(f"reason: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
