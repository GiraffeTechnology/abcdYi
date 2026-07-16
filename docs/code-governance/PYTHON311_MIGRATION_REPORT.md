# Python 3.11 Migration Report — abcdYi (Stage 1)

## Constraint change

| | Before | After |
|---|---|---|
| `requires-python` | `>=3.9` | `>=3.11` |
| CI matrix | 3.11 (unchanged throughout) | 3.11 |
| Dockerfile | `python:3.11-slim` (unchanged) | unchanged |
| `uv.lock` | stale — declared `requires-python = ">=3.11"` and contained `gltg`, never a declared dependency | rebuilt from scratch, 55 packages |

The `>=3.9` floor existed only in `pyproject.toml`. CI, Docker, README and the
committed lockfile all targeted 3.11, so restoring `>=3.11` matches every
environment that actually runs this code. The AIVAN component runs unmodified
on 3.11 (verified: CLI, web server, core E2E, full suite).

## Removed compatibility dependencies

- `eval-type-backport>=0.2.2` — pydantic shim for `X | Y` annotations on 3.9;
  imported nowhere; unnecessary on 3.11.

## Removed unused dependencies (full-tree audit, AIVAN included)

- `aiosqlite` — AIVAN persists via sync SQLAlchemy over stdlib sqlite3
  (`src/aivan/db/session.py`); no async engine, no `sqlite+aiosqlite` URL,
  no import anywhere in the repo.
- `structlog` — zero imports repo-wide.

Explicitly retained after the same audit: `jinja2` (AIVAN web templates),
`python-dotenv` (AIVAN CLI env loader), `python-multipart` (backend OAuth2
form login).

## Compatibility code changes

None required — the codebase is already 3.11-clean (CI proves it).
`from __future__ import annotations` (331 files) and `Optional[...]`
(117 files) left untouched: valid on 3.11, and PRD §5.2 forbids mass
modernization rewrites of stable code.

## CI matrix

Unchanged: all 5 jobs pin Python 3.11. No 3.9 jobs existed.

## Clean install result (from empty environment)

```
rm -rf .venv uv.lock
uv venv --python 3.11        # PASS (CPython 3.11.15)
uv lock                      # PASS — resolved 55 packages
uv sync --all-extras --dev   # PASS
uv run python -m compileall -q src api scripts tests *.py   # exit 0
```

## Test results (clean 3.11 env, PostgreSQL 16 + GLTG CI mock on :8090)

```
uv run pytest tests/ -q   →   1078 passed, 7 skipped, 0 failed
```

5× consecutive-run results from the same commit: see TEST_BASELINE_REPORT.md.
AIVAN product-level validation (integrated entry, core E2E, marketplace E2E,
OpenClaw plugin smoke against the live server): see TEST_BASELINE_REPORT.md.

## Known risks

- Consumers on Python 3.9/3.10 (none referenced anywhere in the repo) must upgrade.
- The old stale `uv.lock` means earlier "locked" installs did not reproduce
  pyproject; the rebuilt lock is the first consistent one.
