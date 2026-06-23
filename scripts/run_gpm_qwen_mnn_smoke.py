#!/usr/bin/env python
"""GPM Qwen MNN Smoke Test.

Only attempts MNN runtime initialization when GPM_ENABLE_LIVE_QWEN_MNN_TESTS=1.
Does not call any cloud or external LLM API.

Usage: uv run python scripts/run_gpm_qwen_mnn_smoke.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> int:
    enabled = os.environ.get("GPM_ENABLE_LIVE_QWEN_MNN_TESTS", "0").strip() == "1"
    if not enabled:
        print("GPM QWEN MNN SMOKE: SKIPPED")
        print(
            "reason: set GPM_ENABLE_LIVE_QWEN_MNN_TESTS=1 to enable live local runtime check"
        )
        return 0

    model_path = os.environ.get("GPM_QWEN_MNN_MODEL_PATH", "").strip()
    if not model_path:
        print("GPM QWEN MNN SMOKE: FAIL")
        print("reason: GPM_QWEN_MNN_MODEL_PATH is required")
        return 1

    try:
        from src.gpm.qwen.qwen_mnn_runtime import QwenMNNRuntime

        runtime = QwenMNNRuntime(model_path=model_path)
        print("GPM QWEN MNN SMOKE: PASS")
        print(f"runtime: {runtime.runtime_name}")
        return 0
    except RuntimeError as exc:
        print("GPM QWEN MNN SMOKE: FAIL")
        print(f"reason: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
