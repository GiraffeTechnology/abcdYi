# Dead Code Removal Report — abcdYi (Stage 1)

Removal criteria: an item is deletable only when it has NO runtime, CLI,
plugin, script, test, deploy, or dynamic-loading reference across the full
tree (backend + AIVAN component + scripts + tests + CI + manifests).
"No direct production import" alone is NOT sufficient — frontend, CLI,
plugin, and standalone-process entrypoints are legitimate consumers.

## Removed

| Path | Reason | Replacement | Runtime references | Test references | Risk | Result |
|---|---|---|---|---|---|---|
| `eval-type-backport` (dep) | Python-3.9-only pydantic shim | native 3.11 annotation evaluation | zero imports | zero | LOW | DELETED |
| `aiosqlite` (dep) | unused: AIVAN's store is sync SQLAlchemy over stdlib sqlite3; backend is asyncpg/PostgreSQL | — | no async-sqlite engine, URL, or import anywhere | zero | LOW | DELETED |
| `structlog` (dep) | unused | — | zero imports repo-wide | zero | LOW | DELETED |
| dev-dep double declaration | duplicate with diverging floors | single `[dependency-groups].dev` | — | — | LOW | MERGED |
| `APP_ENV`, `LOG_LEVEL` in `.env.example` | read by no code | — | none | none | NONE | DELETED |
| 16 root `*_REPORT/RESULT*.md` session reports | historical output presented as current | `docs/archive/` with ARCHIVED banner | none (grep-verified) | none | NONE | ARCHIVED (moved, not deleted) |

## Explicitly retained (with reasons)

| Path | Why kept |
|---|---|
| `src/aivan` (runtime, CLI, web app), `aivan` console script, AIVAN smoke/E2E scripts, `tests/test_aivan_embedded_runtime.py`, OpenClaw plugin assets | first-party AIVAN frontend / digital-employee component of abcdYi; integrated + standalone delivery is a product requirement |
| `jinja2`, `python-dotenv`, `python-multipart` (deps) | in use: AIVAN web templates, AIVAN CLI env loader, backend OAuth2 form login |
| `bm_db_adapter.py`, `bm_db_hardening.py`, `build_schema.py`, `run_bm_e2e_with_db.py`, `verify_integration.py`, `pydantic_stub.py` (root) | live CI harness (`ci.yml`); relocation needs a coordinated CI change → Stage 2 |
| `from __future__ import annotations` / `Optional[...]` style | valid on 3.11; PRD forbids mass modernization rewrites |
| all security/tenant/approval/role-switching tests | protected categories (PRD §6.E.2) |
| `tests/gltg_fake.py`, `tests/ci_gltg_server.py` | explicitly-marked CI contract mock, not a runtime fallback |

## Harness fix (not a removal)

- `scripts/run_aivan_openclaw_plugin_smoke_test.py`: extended the recognised-
  action allowlist with the safety-gate actions documented in
  `src/aivan/execution/safety.py` (`pending_supplier_selection`,
  `pending_product_confirmation`, `pending_requirement_confirmation`).

## Net effect

- Direct dependencies: 19 → 16 (−3), plus the conflicting dev declaration merged.
- Root markdown files: 20 → 4 (README, CHANGELOG, LICENSE_NOTICE, PATENT_NOTICE).
- Source files: unchanged — no product code was deleted; code-mass reduction
  was not a goal of this stage (PRD: 代码量减少不是首要 KPI).
