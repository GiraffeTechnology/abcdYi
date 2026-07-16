# Stage 1 Code Governance — abcdYi Baseline Audit (Phase A)

- **Repository:** `GiraffeTechnology/abcdYi`
- **Audit commit:** `574d28c109c1abd209c1eb2ce87df59432e85da5` (main)
- **Audit date:** 2026-07-16
- **Status:** Read-only audit completed BEFORE any code modification.

## 1. Repository tree (top level)

```
.github/workflows/ci.yml     CI (5 jobs, all Python 3.11)
alembic/                     4-revision linear migration chain
api/                         FastAPI app (api.main:app), 18 route modules, 71 routes
src/                         46 domain packages + src/aivan (embedded AIVAN runtime, 139 files)
tests/                       126 files, 14,210 LOC (unit/api/integration/db/contract)
scripts/                     44 scripts (smoke, seed, e2e, validation)
skills/                      OpenClaw/GPM skills (TypeScript, SKILL.md)
integrations/                openclaw-aivan-plugin (TypeScript, HTTP-boundary)
openclaw/                    giraffe-procurement SKILL.md
frontend/, data/, docs/      assets / fixtures / (docs was empty)
main.py                      helper entry (prints run instructions)
run_bm_e2e_with_db.py        CI-referenced E2E script (root)
bm_db_adapter.py             imported by run_bm_e2e_with_db.py / verify_integration.py
bm_db_hardening.py           imported by the BM DB E2E path
build_schema.py              CI-referenced schema builder
verify_integration.py        CI-referenced 5x verification runner
pydantic_stub.py             fallback shim imported only by verify_integration.py
19 root *.md files           session reports / validation reports / README / notices
```

- Python files: **739** total (src 535 — of which **139 are `src/aivan`**, api 22, tests 126, scripts 44).
- Source LOC (src+api): **41,205**; test LOC: **14,210**.

## 2. Package / import graph (summary)

- Runtime entry: `api.main:app` → `api/routes/*` → `src/*` services/models.
- `src/*` domain packages import each other and `src/db`, `src/integrations`.
- **`src/aivan` is imported by NOTHING in `api/` or `src/` outside itself.**
  Only consumers: 11 `scripts/run_aivan_*.py` smoke scripts (+ `scripts/benchmark_small_model_boundary.py`) and `tests/test_aivan_embedded_runtime.py`.
- No dynamic imports (`importlib`, `import_module`, string module paths) reference `aivan`.
- Circular `api` ↔ `src` dependency: `api/main.py` imports `src.*`; some `src` modules do not import `api` — no true cycle found at module level, but `pythonpath = ["src", "."]` exposes both `src.foo` and bare `foo` namespaces (kept as-is this stage; see Phase D notes).

## 3. API route inventory

18 route modules registered in `api/main.py`; 71 HTTP routes total:
health, auth, participants, projects, dynamic_forms, approval_gates, matching,
rfq, supplier_responses, decision_packets, orders, milestones, qc, logistics,
execution_graph, role_switching, gpm_service.
No route module references `src/aivan`. No dead (unregistered) route modules found.

## 4. CLI / entrypoints

| Entrypoint | Location | Verdict |
|---|---|---|
| `api.main:app` (uvicorn) | Dockerfile.api, README, main.py | KEEP — canonical service entry |
| `main.py` | root helper, prints instructions | KEEP |
| `[project.scripts] aivan = "aivan.cli.main:main"` | pyproject.toml | **DELETE** — belongs to the upstream `aivan` repository, not abcdYi |

## 5. Database models & migrations

- Alembic chain (linear, 4 revisions): `f66f720908c0` → `a1b2c3d4e5f6` → `b2c3d4e5f6a7` → `c3d4e5f6a7b8`.
- `upgrade head` verified against fresh PostgreSQL 16: PASS.
- `src/aivan/db` is a **second, disconnected persistence layer** (part of the embedded runtime) — not referenced by the Alembic chain.
- Cross-repo hazard: revision id `b2c3d4e5f6a7` also exists in Giraffe-JP **with different content** (see cross-repo matrix).

## 6. External service clients

| Service | Canonical client (KEEP) | Duplicate (in `src/aivan`) |
|---|---|---|
| GLTG | `src/integrations/gltg_client.py` (HTTP, fail-closed, "ONLY way to talk to GLTG") + `gltg_leadtime.py`, `src/lead_time/gltg_models.py` | `src/aivan/integrations/gltg.py`, `src/aivan/integrations/gltg_client.py` |
| giraffe-db | `src/gpm/clients/giraffe_db_client.py` | `src/aivan/gpm/giraffe_db_client.py`, `src/aivan/integrations/giraffe_db.py` |
| GPM | `src/gpm/` (service + clients) | `src/aivan/gpm/` |
| OpenClaw | `integrations/openclaw-aivan-plugin` (TypeScript, HTTP to AIVAN API at :8765) + `src/openclaw_skill` | `src/aivan/openclaw/` |
| language-skill | — | `src/aivan/integrations/language_skill_client.py` |

Removing `src/aivan` eliminates every duplicate client/adapter/DTO pair in one step; each remaining capability has exactly one client.

## 7. Duplicate modules

- **Two AIVAN runtimes** exist in the org: the canonical `GiraffeTechnology/aivan` repository and the copy embedded at `src/aivan` (commit `91c7fc3` "Embed AIVAN runtime with Python 3.9 support"). The embed is the direct cause of the Python 3.9 downgrade (`requires-python = ">=3.9"`, `eval-type-backport`).
- Within non-aivan `src/`, no same-capability duplicate client/DTO/env-parser pairs were found.

## 8. Dead code candidates (evidence per §4.1 of the PRD)

| Path | Production import | Dynamic import | Route | Entrypoint | Migration | Deploy | Plugin manifest | Docs claim current | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| `src/aivan/` (139 files) | none | none | none | pyproject `aivan` script only | none | none | plugin uses HTTP + upstream repo URL | none (README/CHANGELOG silent) | **DELETE** (canonical owner: `aivan` repo) |
| `scripts/run_aivan_*.py` (11 files) | n/a (scripts) | — | — | — | — | not in CI/Makefile | — | — | **DELETE** with the embed |
| `scripts/benchmark_small_model_boundary.py` | imports `aivan` | — | — | — | — | not in CI | — | — | **DELETE** with the embed |
| `tests/test_aivan_embedded_runtime.py` | tests the embed itself | — | — | — | — | — | — | — | **DELETE** with the embed |
| root session/validation reports (15 files) | n/a | — | — | — | — | — | — | historical | **ARCHIVE** to `docs/archive/` |
| `bm_db_adapter.py`, `bm_db_hardening.py`, `build_schema.py`, `run_bm_e2e_with_db.py`, `verify_integration.py`, `pydantic_stub.py` | referenced by CI (`ci.yml` lines 88–106) | — | — | — | — | CI | — | — | **KEEP** (live CI harness; MOVE to `scripts/` deferred — REVIEW) |

## 9. Scripts classification (44 files)

- **aivan smoke/e2e (12)** — test the embedded runtime only → DELETE with embed.
- **DB / seed / init (7)** — `init_db.py`, `reset_db.py`, `seed_*.py` → KEEP.
- **domain e2e / MVP (17)** — `run_role_switching_mvp.py` (invoked by test suite), `run_bm_e2e_mvp.py`, etc. → KEEP.
- **GPM smoke (8)** — live/local model smoke tools → KEEP (marked live/external).

## 10. Tests classification (126 files, baseline run)

Baseline (main, Python 3.11, PostgreSQL 16 + `tests/ci_gltg_server.py` on :8090):
**1081 passed, 7 skipped, 0 failed** (without GLTG mock: 1 env-dependent failure in `TestE2EScript`, fail-closed by design; without PostgreSQL: 73 errors — integration tests).

Categories: unit (`tests/unit`), api (`tests/api`), integration (`tests/integration`), db (`tests/db`), contract (GLTG fake at `tests/gltg_fake.py` + `tests/ci_gltg_server.py`, explicitly marked CI-only mock, not a runtime fallback), e2e (subprocess scripts). Security-critical suites present: tenant isolation, approval replay (`consumed_at`), role switching, auth. `tests/test_aivan_embedded_runtime.py` covers only the embed → delete with it.

## 11. Documentation drift

- README does not mention the embedded AIVAN runtime (it describes AIVAN as external architecture) — consistent with removal.
- 15 root-level historical reports (GPM_SESSION_A–F, BM_DB, PR11/PR12, validation/test results) present stale test counts and completed-session claims as if current → ARCHIVE.
- README quick-start and CI are already Python 3.11 while `pyproject.toml` says `>=3.9` → contradiction resolved by Phase B.

## 12. Environment variable usage matrix

See `ENVIRONMENT_VARIABLE_MATRIX.md` (Stage 1 deliverable). Highlights: `DATABASE_URL`, `SECRET_KEY` (fail-fast weak-key guard at startup), `GLTG_API_BASE_URL`/`GLTG_API_TIMEOUT_SECONDS`, `GIRAFFE_DB_*`, `GPM_*`, `QWEN_*`/`DASHSCOPE_API_KEY`, `LLM_ENABLE_REAL_CALLS`, `QC_ALLOW_*` (fail-closed switches), `OPENCLAW_*`. `AIVAN_*` variables are read **only** inside `src/aivan` → obsolete after removal.

## 13. Python 3.9 compatibility residue

- `requires-python = ">=3.9"` (downgraded by the AIVAN embed commit; CI and Dockerfile stayed on 3.11).
- `eval-type-backport>=0.2.2` dependency — never imported directly; present only so pydantic can evaluate `X | Y` annotations on 3.9. Unnecessary on 3.11.
- 331 files use `from __future__ import annotations` (harmless on 3.11 — KEEP, no mass rewrite per PRD §5.2).
- 117 files still use `Optional[...]` etc. — valid syntax on 3.11; no mechanical rewrite this stage.
- No other 3.9-only backports found.

## 14. Canonical owner recommendations

See `STAGE1_CROSS_REPO_OWNERSHIP_MATRIX.md`.

## 15. Deletion risk assessment

- `src/aivan` removal: LOW — no production reference (evidence in §8); recoverable from git history (`91c7fc3`) and canonical upstream repo.
- Report archival: NONE (moves, not deletions).
- Dependency removals (`eval-type-backport`, `aiosqlite`, `jinja2`, `python-dotenv`, `structlog`): LOW — zero imports in repo (dotenv only inside `src/aivan`); verified by string scan of all `.py` files.

## 16. Currently runnable commands (verified in this audit)

```
uv venv --python 3.11 && uv sync --all-extras --dev       # PASS
uv run alembic upgrade head                                # PASS (fresh PG16)
uv run pytest tests/ -q                                    # PASS (PG16 + tests/ci_gltg_server.py :8090)
uv run uvicorn api.main:app                                # canonical serve path
```

## 17. Currently failing commands (baseline, main)

```
uv run pytest tests/ -q            # without PostgreSQL: 73 errors; without GLTG mock: 1 failure (fail-closed, by design)
aivan (console script)             # entrypoint for the embedded runtime; not a product entry
```

## 18. Deployment entry

`Dockerfile.api` → `uvicorn api.main:app` on python:3.11-slim; `docker-compose.yml` (api + postgres). No reference to `src/aivan`.

## 19. Cross-repo duplication with Giraffe-JP

Giraffe-JP `src/` contains 326 files; **317 also exist in abcdYi** (175 byte-identical, 142 diverged forks). See `STAGE1_CROSS_REPO_OWNERSHIP_MATRIX.md`.

## 20. Disposition summary

| Item | Action |
|---|---|
| `src/aivan` + aivan scripts + aivan test + `[project.scripts] aivan` + wheel `src/aivan` entry | DELETE |
| `requires-python`, `eval-type-backport` | RESTORE >=3.11 / DELETE |
| unused deps (`aiosqlite`, `jinja2`, `python-dotenv`, `structlog`) | DELETE |
| root historical reports (15) | MOVE → `docs/archive/` (ARCHIVED banner) |
| CI harness root scripts (`bm_db_*`, `run_bm_e2e_with_db`, `build_schema`, `verify_integration`, `pydantic_stub`) | KEEP (REVIEW: relocate to `scripts/` in a later stage, requires CI edit) |
| dev-dependency double declaration (`optional-dependencies.dev` vs `dependency-groups.dev`) | MERGE (single source: `dependency-groups.dev`) |
| all domain `src/*`, `api/*`, tests, migrations | KEEP |
