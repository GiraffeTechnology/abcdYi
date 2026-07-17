# Stage 1 Code Governance — abcdYi Baseline Audit

- **Repository:** `GiraffeTechnology/abcdYi`
- **Audit base commit:** `574d28c109c1abd209c1eb2ce87df59432e85da5` (main)
- **Audit date:** 2026-07-16

## 1. Product structure

```
abcdYi
├── AIVAN frontend / digital employee interface   (src/aivan)
├── apparel / textile / handicraft workflows      (src/* domain packages)
├── B-side / M-side role switching                (src/actors, src/roles, src/b_side, src/m_side)
├── GPM integration                               (src/gpm)
├── GLTG integration                              (src/integrations/gltg_client.py, gltg_leadtime.py)
├── giraffe-db integration                        (src/gpm/clients/giraffe_db_client.py)
├── human approval                                (src/approval_gates + consumed_at replay protection)
├── execution graph                               (src/execution_graph)
└── OpenClaw / channel integration                (integrations/openclaw-aivan-plugin, src/openclaw_skill, src/channels)
```

**Product ownership:** AIVAN is a first-party frontend and digital-employee
component of abcdYi.

**Source ownership:** AIVAN may have an independently maintained canonical
codebase, while abcdYi must deliver a compatible first-party AIVAN runtime or
package as part of the standard product.

**Deployment:** AIVAN supports both integrated and standalone deployment.

## 2. Repository tree (top level)

```
.github/workflows/ci.yml     CI (5 jobs, all Python 3.11)
alembic/                     4-revision linear migration chain (backend DB)
api/                         backend FastAPI app (api.main:app), 18 route modules, 71 routes
src/                         46 domain packages + src/aivan (AIVAN component, 139 files)
tests/                       126 files (unit/api/integration/db/contract/e2e)
scripts/                     44 scripts (smoke, seed, e2e, validation)
skills/                      OpenClaw/GPM skills (TypeScript)
integrations/                openclaw-aivan-plugin (TypeScript channel plugin)
openclaw/                    giraffe-procurement SKILL.md
main.py                      helper entry
run_bm_e2e_with_db.py, bm_db_adapter.py, bm_db_hardening.py,
build_schema.py, verify_integration.py, pydantic_stub.py
                             BM DB CI harness (referenced by ci.yml)
```

## 3. Entrypoints (all first-party, all retained)

| Entrypoint | Serves |
|---|---|
| `api.main:app` (uvicorn; Dockerfile.api) | abcdYi backend API |
| `aivan` console script → `aivan.cli.main:main` | AIVAN CLI (init/serve/demo/import/risk-check) |
| `aivan serve` → `aivan.api.main:app` on :8765 | AIVAN web frontend / digital-employee interface (Jinja2 UI + JSON API) |
| `integrations/openclaw-aivan-plugin` | OpenClaw channel plugin; talks to the AIVAN API (`aivanBaseUrl`, default `http://127.0.0.1:8765`) |

Frontend, CLI, plugin and standalone-process entrypoints are legitimate
integration points; "not imported by the backend" is NOT treated as evidence
of dead code (they are consumed by users, channels, and deploy tooling).

Integrated deployment: install abcdYi → AIVAN is available (`aivan serve`) →
natural-language instruction → AIVAN invokes abcdYi business capabilities.
Standalone deployment: deploy AIVAN separately → connect over its stable API.

## 4. Import / dependency graph (summary)

- Backend: `api/main.py` → `api/routes/*` → `src/*` services/models.
- AIVAN component: self-contained package under `src/aivan` with its own
  web app, CLI, agents, execution policies (safety gates, human approval),
  integration clients (GLTG, giraffe-db, language-skill, OpenClaw) and a
  component-local persistence layer (sync SQLAlchemy; `AIVAN_DB_URL`,
  default local sqlite) that is intentionally separate from the backend's
  Alembic-managed PostgreSQL schema.
- Integration clients exist at two levels by design: backend clients
  (`src/integrations`, `src/gpm`) serve backend workflows; AIVAN's clients
  (`src/aivan/integrations`, `src/aivan/gpm`) serve the AIVAN runtime, which
  must also operate in standalone deployment. Convergence of shared DTO/client
  code into one internal library is a candidate for a later stage
  (REVIEW_REQUIRED), not a Stage 1 deletion target.

## 5. API routes

Backend: 18 route modules, 71 routes registered in `api/main.py` (health,
auth, participants, projects, dynamic_forms, approval_gates, matching, rfq,
supplier_responses, decision_packets, orders, milestones, qc, logistics,
execution_graph, role_switching, gpm_service). AIVAN web/API routes live in
`src/aivan/api/main.py` (`/api/health`, `/api/openclaw/events`, `/api/drafts`,
approval endpoints, web UI). No dead routers found in either app.

## 6. Database & migrations

- Backend: linear 4-revision Alembic chain; `upgrade head`/`downgrade base`/
  `upgrade head` verified on fresh PostgreSQL 16.
- AIVAN: component-local store via `AIVAN_DB_URL` (sqlite by default,
  WAL + FK pragmas), initialized by `aivan init`; not part of the backend
  Alembic chain by design (standalone deployment requirement).
- Cross-repo hazard: Alembic revision id `b2c3d4e5f6a7` also exists in
  Giraffe-JP with different content (see cross-repo matrix) — REVIEW_REQUIRED.

## 7. Python 3.9 residue (Phase B input)

- `requires-python = ">=3.9"` in pyproject only; CI, Dockerfile and the
  committed lockfile all targeted 3.11 (the lock even declared
  `requires-python = ">=3.11"` and contained a stale `gltg` entry that was
  never a declared dependency).
- `eval-type-backport` — pydantic annotation shim needed only on 3.9;
  imported nowhere.
- `from __future__ import annotations` (331 files) / `Optional[...]`
  (117 files): valid on 3.11; retained (no mass modernization per PRD §5.2).

## 8. Dependency findings (full tree, AIVAN included)

| Dependency | Verdict | Evidence |
|---|---|---|
| jinja2 | KEEP | AIVAN web frontend (`src/aivan/api/main.py`: `Jinja2Templates`, `src/aivan/app/templates/`) |
| python-dotenv | KEEP | AIVAN CLI env loader (`src/aivan/cli/main.py`) |
| python-multipart | KEEP | backend OAuth2 form login (`api/routes/auth.py`) |
| aiosqlite | REMOVE | AIVAN persists via **sync** SQLAlchemy over stdlib sqlite3 (`src/aivan/db/session.py`); no async engine, no `sqlite+aiosqlite` URL, no import anywhere |
| structlog | REMOVE | zero imports repo-wide |
| eval-type-backport | REMOVE | 3.9-only shim, zero imports, 3.11 baseline |
| asyncpg + psycopg2-binary | KEEP both | async app driver + sync Alembic/CI driver (documented split) |

Dev dependencies were declared twice (`optional-dependencies.dev` and
`dependency-groups.dev`) with diverging httpx floors → consolidate.

## 9. Scripts classification (44)

- AIVAN smoke/E2E/demo (12) — exercise the AIVAN component (core E2E,
  marketplace, OpenClaw plugin/gateway/install, private-domain RFQ, risk,
  whitelist, benchmark) → KEEP (product validation surface).
- DB / seed / init (7) → KEEP. Domain E2E / MVP (17) → KEEP (one is invoked
  by the test suite). GPM smoke (8) → KEEP (live/external, excluded from CI).

## 10. Tests classification

unit (`tests/unit`, 44 files) / api (`tests/api`, 16) / integration
(`tests/integration`, 12) / db (`tests/db`, 6) / e2e + component suites
(root, 35 incl. AIVAN runtime test) / contract (GLTG CI mock
`tests/gltg_fake.py` + `tests/ci_gltg_server.py`, explicitly marked CI-only).
Security-critical suites: tenant isolation, approval replay, role switching,
auth, fail-closed startup. No keyword-only README tests found in this repo.

## 11. Documentation drift

- 16 root-level historical session/validation reports presented past runs as
  current → ARCHIVE to `docs/archive/` with banner.
- `.env.example` documented `APP_ENV`/`LOG_LEVEL`, which no code reads → remove.
- CHANGELOG header said "Giraffe Agent" for the abcdYi product → fix wording.
- README quick facts vs pyproject Python floor → resolved by Phase B.

## 12. Currently runnable commands (verified)

```
uv venv --python 3.11 && uv sync --all-extras --dev   # PASS
uv run alembic upgrade head                            # PASS (fresh PG16)
uv run pytest tests/ -q                                # PASS (PG16 + GLTG CI mock :8090)
uv run uvicorn api.main:app                            # backend serve
uv run aivan serve                                     # AIVAN frontend on :8765
uv run python scripts/run_aivan_e2e.py                 # AIVAN core E2E: PASS
```

## 13. Environment-dependent commands

- Full suite requires PostgreSQL and the GLTG CI mock (same as CI).
- `scripts/run_aivan_private_domain_rfq_e2e.py` requires the live GLTG
  service (AIVAN's GLTG API surface differs from the abcdYi CI mock) —
  classified live/external.

## 14. Disposition summary

| Item | Action |
|---|---|
| `requires-python` / `eval-type-backport` | RESTORE >=3.11 / DELETE |
| `aiosqlite`, `structlog` | DELETE (unused, full-tree evidence) |
| `jinja2`, `python-dotenv`, `python-multipart` | KEEP (in use) |
| dev-dependency double declaration | MERGE |
| stale `uv.lock` | REBUILD |
| 16 root historical reports | MOVE → `docs/archive/` |
| unread `.env.example` vars (APP_ENV, LOG_LEVEL) | DELETE |
| AIVAN component (runtime, CLI, web app, scripts, tests, plugin assets) | KEEP (first-party product component) |
| all domain `src/*`, `api/*`, migrations, security tests | KEEP |
| BM DB CI harness at root | KEEP (live CI; relocation = Stage 2 REVIEW) |
| backend↔AIVAN shared DTO/client convergence | REVIEW_REQUIRED (later stage) |
