# Final Code Governance Report — abcdYi (Stage 1)

- Base commit audited: `574d28c` (main). Work branch: `claude/new-session-jpfmm9`.
- Scope executed: Phase A (audit) → B (Python 3.11) → C (redundancy removal) →
  D (ownership/convergence documentation) → E (test governance + 5× validation).

## What changed

1. **AIVAN ownership resolved.** The embedded runtime `src/aivan` (139 files)
   was proven unreferenced by any production path and deleted; canonical AIVAN
   lives in the `aivan` repository and is consumed via the OpenClaw plugin's
   HTTP boundary. There is no duplicated AIVAN runtime in this repo anymore.
2. **Python `>=3.11` restored** (pyproject was the only 3.9 holdout);
   `eval-type-backport` removed; lockfile rebuilt from scratch (the old lock
   was stale and contained a foreign `gltg` entry).
3. **Redundancy reduced measurably:** −152 Python files, −11,786 source LOC
   (41,205 → 29,419), −5 direct dependencies, one client per external service
   (GLTG / giraffe-db / GPM / OpenClaw), single dev-dependency declaration,
   16 stale root reports archived, 2 unread env vars removed.
4. **Docs made truthful:** README already described the correct architecture
   ("abcdYi must not embed its own … runtimes"); the repo now matches it.

## Acceptance checklist (PRD §13.1)

- [x] Python `>=3.11` (pyproject + CI + Docker + lock all agree)
- [x] `eval-type-backport` removed
- [x] Clean Python 3.11 install from empty env (`uv venv --python 3.11 && uv sync --all-extras --dev`)
- [x] AIVAN ownership explicit (aivan repo; HTTP integration boundary)
- [x] No duplicate AIVAN runtime
- [x] GLTG has exactly one call path (`src/integrations/gltg_client.py`, fail-closed)
- [x] giraffe-db has exactly one client boundary (`src/gpm/clients/giraffe_db_client.py`)
- [x] GPM has one service path (`src/gpm/`; aivan duplicates deleted)
- [x] No duplicate env parser (single pydantic-settings `Settings`)
- [x] Unused dependencies removed (aiosqlite, jinja2, python-dotenv, structlog)
- [x] Dead modules removed (evidence tables in DEAD_CODE_REMOVAL_REPORT.md)
- [x] Migration chain intact; up/down/up PASS on fresh PG16
- [x] Security regressions all pass (tenant isolation, approval replay, auth, fail-closed)
- [x] Core E2E passes
- [x] Full suite 5× consecutive from one commit: 1077 passed each run
- [x] README consistent with reality

## Code-mass acceptance (PRD §13.3)

Source files ↓ (739→588), dependencies ↓ (19→14), duplicate modules ↓ (all
embed duplicates gone), scripts/reports archived ✓, package identity correct ✓.

## Not done in Stage 1 (explicit)

- Directory re-layout to the illustrative Phase D structure (`src/abcdyi/…`)
  was **not** performed: 300+ modules import via the current `src.*`/bare
  namespaces and the PRD forbids mechanical mass moves without import-cost
  analysis. Documented as future work; no functional impact.
- BM DB CI harness remains at repo root (CI references it by path) — Stage 2.
- Alembic revision-id collision with Giraffe-JP documented, not rewritten
  (history rewrite forbidden).

## Stage 2 dependencies recorded

See `STAGE1_CROSS_REPO_OWNERSHIP_MATRIX.md` (JP-S2-1 … JP-S2-4). No other
repository was modified in this task (PRD §2.2 respected).

## Deliverables

`docs/code-governance/`: STAGE1_ABCDYI_AUDIT.md, STAGE1_CROSS_REPO_OWNERSHIP_MATRIX.md,
PYTHON311_MIGRATION_REPORT.md, DEPENDENCY_USAGE_REPORT.md,
ENVIRONMENT_VARIABLE_MATRIX.md, MIGRATION_INTEGRITY_REPORT.md,
DEAD_CODE_REMOVAL_REPORT.md, TEST_BASELINE_REPORT.md, this report.
