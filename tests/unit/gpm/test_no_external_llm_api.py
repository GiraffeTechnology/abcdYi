"""Assert no external LLM API imports exist in src/gpm/."""
from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

FORBIDDEN = [
    "openai",
    "anthropic",
    "dashscope",
    "google.generativeai",
    "deepseek",
]

GPM_ROOT = Path(__file__).parent.parent.parent.parent / "src" / "gpm"


def _collect_imports(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _all_gpm_python_files() -> list[Path]:
    if not GPM_ROOT.exists():
        return []
    return list(GPM_ROOT.rglob("*.py"))


@pytest.mark.parametrize("py_file", _all_gpm_python_files() or [Path("/dev/null")])
def test_no_forbidden_import(py_file: Path) -> None:
    if py_file.name == "/dev/null" or not py_file.exists():
        return
    source = py_file.read_text(encoding="utf-8")
    imports = _collect_imports(source)
    for imp in imports:
        for forbidden in FORBIDDEN:
            assert not imp.startswith(forbidden), (
                f"{py_file.relative_to(GPM_ROOT.parent.parent)} imports forbidden module '{imp}'"
            )
