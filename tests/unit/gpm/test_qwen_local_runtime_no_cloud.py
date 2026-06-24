"""Tests for QwenLocalRuntime: mock mode, non-mock failure, and no cloud imports."""
from __future__ import annotations

import ast
import os

import pytest

from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime


# ── mock mode ─────────────────────────────────────────────────────────────────

def test_mock_mode_no_model_path_required() -> None:
    runtime = QwenLocalRuntime(mock_mode=True)
    assert runtime.runtime_mode == "mock"


def test_mock_mode_generate_json_deterministic() -> None:
    runtime = QwenLocalRuntime(mock_mode=True)
    prompt = "men cotton shirt OEM Japan\nevidence_ids: []"
    out1 = runtime.generate_json(prompt, schema_name="gpm_normalization")
    out2 = runtime.generate_json(prompt, schema_name="gpm_normalization")
    assert out1 == out2


def test_mock_mode_returns_dict() -> None:
    runtime = QwenLocalRuntime(mock_mode=True)
    result = runtime.generate_json("men cotton shirt\nevidence_ids: []", schema_name="gpm_normalization")
    assert isinstance(result, dict)


def test_mock_mode_required_keys() -> None:
    runtime = QwenLocalRuntime(mock_mode=True)
    result = runtime.generate_json("cotton shirt men\nevidence_ids: []", schema_name="gpm_normalization")
    for key in ("normalized_product_type", "is_comparable", "comparability_score", "evidence_ids"):
        assert key in result, f"Missing key: {key}"


def test_mock_mode_shirt_scenario_score() -> None:
    runtime = QwenLocalRuntime(mock_mode=True)
    result = runtime.generate_json(
        "men cotton shirt OEM 100% cotton Japan\nevidence_ids: []",
        schema_name="gpm_normalization",
    )
    assert result["comparability_score"] == 0.85
    assert result["is_comparable"] is True


# ── non-mock mode raises when MNN unavailable ─────────────────────────────────

def test_non_mock_no_model_path_raises() -> None:
    saved = {k: os.environ.pop(k, None) for k in (
        "GPM_QWEN_MNN_MODEL_PATH", "GPM_LLM_RUNTIME_MODE", "GPM_QWEN_RUNTIME_MODE",
        "GPM_RUNTIME_PROFILE",
    )}
    os.environ["GPM_LLM_RUNTIME_MODE"] = "mnn"
    try:
        with pytest.raises(RuntimeError):
            QwenLocalRuntime(model_path=None, mock_mode=False)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


def test_non_mock_nonexistent_path_raises(tmp_path: object) -> None:
    with pytest.raises(RuntimeError, match="does not exist"):
        QwenLocalRuntime(model_path="/nonexistent/path/to/model.mnn", mock_mode=False)


def test_non_mock_does_not_silently_fall_back_to_cloud() -> None:
    """If MNN is unavailable, RuntimeError must be raised — no cloud fallback."""
    saved = {k: os.environ.pop(k, None) for k in (
        "GPM_QWEN_MNN_MODEL_PATH", "GPM_LLM_RUNTIME_MODE", "GPM_QWEN_RUNTIME_MODE",
        "GPM_RUNTIME_PROFILE",
    )}
    os.environ["GPM_LLM_RUNTIME_MODE"] = "mnn"
    try:
        with pytest.raises(RuntimeError):
            QwenLocalRuntime(model_path=None, mock_mode=False)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


# ── AST guard: no external LLM imports ───────────────────────────────────────

_FORBIDDEN_MODULES = ("openai", "anthropic", "dashscope", "google.generativeai", "deepseek")
_GPM_SRC_DIRS = [
    "src/gpm/llm_adapters",
    "src/gpm/qwen",
    "src/gpm/context",
    "src/gpm/prompts",
    "src/gpm/validators",
    "src/gpm/services",
]


def _collect_imports_from_file(path: str) -> list[str]:
    with open(path) as f:
        tree = ast.parse(f.read(), filename=path)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_no_external_llm_imports_in_gpm_src() -> None:
    import pathlib
    repo_root = pathlib.Path(".")
    violations: list[str] = []
    for src_dir in _GPM_SRC_DIRS:
        for py_file in repo_root.glob(f"{src_dir}/**/*.py"):
            found = _collect_imports_from_file(str(py_file))
            for forbidden in _FORBIDDEN_MODULES:
                for imp in found:
                    if imp == forbidden or imp.startswith(f"{forbidden}."):
                        violations.append(f"{py_file}: imports {imp!r}")
    assert not violations, "Forbidden external LLM imports found:\n" + "\n".join(violations)
