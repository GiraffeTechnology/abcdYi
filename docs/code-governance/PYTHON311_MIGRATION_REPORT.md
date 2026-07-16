# Python 3.11 Migration Report — abcdYi (Stage 1)

## Constraint change

| | Before | After |
|---|---|---|
| `requires-python` | `>=3.9` | `>=3.11` |
| CI matrix | 3.11 (never changed) | 3.11 |
| Dockerfile | `python:3.11-slim` (never changed) | unchanged |
| `uv.lock` | **stale** — still declared `requires-python = ">=3.11"` and contained `gltg` (never an abcdYi dependency; evidence the lock was copied/stale after the 3.9 downgrade commit `91c7fc3`) | rebuilt from scratch, 54 packages |

The 3.9 downgrade existed only in `pyproject.toml` and was introduced by the
AIVAN embed commit (`91c7fc3` "Embed AIVAN runtime with Python 3.9 support").
CI, Docker, README and the lockfile stayed on 3.11 the whole time, so
restoring `>=3.11` matches every environment that actually ran this code.

## Removed compatibility dependencies

- `eval-type-backport>=0.2.2` — pydantic shim for `X | Y` annotations on 3.9;
  never imported anywhere in the repo; unnecessary on 3.11.

## Removed unused dependencies (same lock rebuild)

- `aiosqlite` — zero references (no sqlite URL, no import).
- `jinja2` — zero references.
- `python-dotenv` — imported only by the deleted `src/aivan/cli/main.py`.
- `structlog` — zero references.

## Compatibility code changes

- None required outside the deleted `src/aivan` tree. The remaining codebase
  was already 3.11-clean (CI proves it).
- `from __future__ import annotations` (331 files) and `Optional[...]`
  (117 files) were deliberately left alone — both are valid on 3.11 and the
  PRD forbids mass modernization rewrites of stable code (§5.2).

## CI matrix

Unchanged: all 5 jobs pin Python 3.11 (`.github/workflows/ci.yml`). No 3.9
jobs existed to remove.

## Clean install result (from empty environment)

```
rm -rf .venv uv.lock
uv venv --python 3.11        # PASS (CPython 3.11.15)
uv lock                      # PASS — resolved 54 packages
uv sync --all-extras --dev   # PASS
uv run python -m compileall -q src api scripts tests *.py   # exit 0
```

## Dependency diff (lock names, before → after)

Removed: `eval-type-backport`*, `aiosqlite`*, `jinja2`*, `python-dotenv`
(now transitive only via uvicorn[standard]), `structlog`, `gltg` (stale lock
entry, never declared).
*Note: because the old lock was stale, some removed pyproject deps were
already absent from it; the authoritative before-state is `pyproject.toml`
at `574d28c`.

## Test results (clean 3.11 env, PostgreSQL 16 + GLTG CI mock on :8090)

```
uv run pytest tests/ -q   →   1077 passed, 7 skipped, 0 failed
```

5× consecutive-run results from the same commit: see TEST_BASELINE_REPORT.md.

## Known risks

- Consumers who installed abcdYi on Python 3.9/3.10 (if any) must upgrade;
  no such deployment is referenced anywhere in the repo.
- The old stale `uv.lock` means previous "locked" installs were not actually
  reproducing pyproject; the new lock is the first consistent one.
