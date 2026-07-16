# Dead Code Removal Report — abcdYi (Stage 1)

Every deletion was cross-verified with: ripgrep string scan (py + non-py),
import scan, route registry, CLI/entrypoint registry, plugin manifest scan,
CI/deploy file scan, migration chain review, and a full-suite run after
removal. No deletion happened before the Phase A audit was written.

| Path | Reason | Replacement | Runtime references | Test references | Risk | Result |
|---|---|---|---|---|---|---|
| `src/aivan/` (139 files, ~13.9k LOC) | duplicate AIVAN runtime; canonical owner is the `aivan` repository; direct cause of the Python 3.9 downgrade | canonical AIVAN service via OpenClaw plugin HTTP boundary (`integrations/openclaw-aivan-plugin`, :8765) | none (grep + import scan: 0 in `api/`, 0 in non-aivan `src/`, 0 dynamic imports, 0 in CI/Docker/Makefile/manifests/migrations) | only `tests/test_aivan_embedded_runtime.py` (tested the embed itself) | LOW — recoverable from git (`91c7fc3`) and upstream repo | DELETED; suite green |
| `scripts/run_aivan_*.py` (10) + `scripts/run_aivan_openclaw_*.py` | smoke scripts exercising only the deleted embed | none needed | not referenced by CI/Makefile | none | LOW | DELETED |
| `scripts/benchmark_small_model_boundary.py` | imports the deleted embed | none | none | none | LOW | DELETED |
| `tests/test_aivan_embedded_runtime.py` | verified only the deleted implementation (PRD Phase E deletable category) | — | — | — | LOW | DELETED |
| `[project.scripts] aivan` entrypoint | CLI of the aivan product, not abcdYi | aivan repo | console-script only | none | LOW | DELETED |
| `eval-type-backport`, `aiosqlite`, `jinja2`, `python-dotenv`, `structlog` (deps) | unused (see DEPENDENCY_USAGE_REPORT.md) | — | zero imports | zero | LOW | DELETED |
| `APP_ENV`, `LOG_LEVEL` in `.env.example` | read by no code | — | none | none | NONE | DELETED |
| 16 root `*_REPORT/RESULT*.md` session reports | historical session output presented as current | `docs/archive/` with ARCHIVED banner | none (grep-verified) | none | NONE | ARCHIVED (moved, not deleted) |

## Explicitly NOT removed (with reasons)

| Path | Why kept |
|---|---|
| `bm_db_adapter.py`, `bm_db_hardening.py`, `build_schema.py`, `run_bm_e2e_with_db.py`, `verify_integration.py`, `pydantic_stub.py` (root) | live CI harness (`ci.yml` lines 88–106); relocation to `scripts/` needs a coordinated CI change → Stage 2 |
| `from __future__ import annotations` / `Optional[...]` style | valid on 3.11; PRD forbids mass modernization rewrites |
| all security/tenant/approval/role-switching tests | protected categories (PRD §6.E.2) |
| `tests/gltg_fake.py`, `tests/ci_gltg_server.py` | explicitly-marked CI contract mock, not a runtime fallback |

## Net effect

- Python files: 739 → 587 (−152)
- Source LOC (src+api): 41,205 → ~27,300 (−13,900)
- Dependencies (direct): 19 → 14 (−5)
- Root markdown files: 20 → 4 (README, CHANGELOG, LICENSE_NOTICE, PATENT_NOTICE)
- Duplicate runtimes: 2 AIVAN runtimes → AIVAN not duplicated in this repo
- Duplicate clients (GLTG / giraffe-db / GPM / OpenClaw): each now has exactly one implementation
