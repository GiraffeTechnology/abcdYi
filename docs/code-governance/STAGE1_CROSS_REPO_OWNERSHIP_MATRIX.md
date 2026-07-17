# Stage 1 — Cross-Repo Ownership Matrix (abcdYi ↔ Giraffe-JP)

Audited at abcdYi `574d28c` / Giraffe-JP `41f24fb` (2026-07-16).
Measured duplication: Giraffe-JP `src/` = 326 files, of which 317 exist in
abcdYi (175 byte-identical, 142 diverged forks).

## AIVAN ownership statement

```
Product ownership:
AIVAN is a first-party frontend and digital-employee component of abcdYi.

Source ownership:
AIVAN may have an independently maintained canonical codebase, while abcdYi
must deliver a compatible first-party AIVAN runtime or package as part of the
standard product.

Deployment:
AIVAN supports both integrated and standalone deployment.
```

| Capability | abcdYi | Giraffe-JP | Canonical owner | Action |
|---|---|---|---|---|
| AIVAN frontend / digital-employee runtime | `src/aivan` (first-party component; CLI + web app + agents) | absent | **abcdYi product** (source may also be maintained in the `aivan` repo; abcdYi ships a compatible first-party runtime) | KEEP integrated delivery; keep standalone-deployment compatibility (stable AIVAN API) |
| GLTG client (backend) | `src/integrations/gltg_client.py` (HTTP, fail-closed) | vendored engine `libs/GLTG` + local lead-time modules | **`GLTG` repository** (external service) | abcdYi: KEEP HTTP client. JP: KEEP vendored copy this stage with evidence; **Stage 2 handoff JP-S2-1**: migrate to HTTP client |
| GLTG client (AIVAN component) | `src/aivan/integrations/gltg.py` (component client for standalone mode) | absent | AIVAN component | KEEP; DTO/client convergence with backend client = REVIEW_REQUIRED (later stage) |
| GPM client/service | `src/gpm/` (backend) + `src/aivan/gpm` (component) | absent | **abcdYi** (`GPM` service external) | KEEP; same convergence REVIEW as above |
| giraffe-db client | `src/gpm/clients/giraffe_db_client.py` (backend), `src/aivan/integrations/giraffe_db.py` (component) | BM DB harness (CI-only) | **`giraffe-db` repository** (external API) | KEEP per-component boundary; convergence REVIEW_REQUIRED |
| role switching | `src/actors`, `src/roles`, `api/routes/role_switching.py` | diverged copy | **abcdYi** | JP copy frozen; extraction to dependency = **Stage 2 handoff JP-S2-2** (Option A) |
| communication | `src/channels`, `src/order_confirmation` | diverged copy + `src/giraffe_jp/communication.py` (JP policy layer) | generic: **abcdYi**; JP policy layer: **Giraffe-JP** | keep JP layer in JP; generic copy frozen (JP-S2-2) |
| formalwear | `src/apparel_platform` (generic apparel) | `src/giraffe_jp/formalwear.py` + routes (C2B2M extension) | **Giraffe-JP** | KEEP in JP |
| message permissions | `src/permissions` (generic) | diverged copy + `src/giraffe_jp/message_permissions.py` | generic: **abcdYi**; JP layer: **Giraffe-JP** | as communication |
| approval gates | `src/approval_gates` + `consumed_at` replay protection | diverged copy | **abcdYi** | JP copy frozen (JP-S2-2); replay-protection semantics must not diverge — REVIEW_REQUIRED on any future edit |
| tenant scope | `src/db/tenant_scope.py` + route-level filters | route-level filters only | **abcdYi** | REVIEW_REQUIRED: JP parity check (Stage 2, JP-S2-4) |
| auth | `api/auth.py` (jose/passlib/OAuth2) | byte-similar copy | **abcdYi** | frozen copy (JP-S2-2) |
| execution events (append-only) | `src/execution_graph` | diverged copy | **abcdYi** | frozen copy; append-only invariant tests kept in both |
| OpenClaw plugin | `integrations/openclaw-aivan-plugin` (TS; talks to the AIVAN API) | `openclaw/skills` only | **abcdYi** (plugin), upstream OpenClaw external | KEEP |
| API schemas | `api/routes/*` pydantic schemas | copy + 6 `giraffe_jp_*` route modules | shared: **abcdYi**; `giraffe_jp_*`: **Giraffe-JP** | frozen (JP-S2-2) |
| shared DTOs | `src/core_schema`, `src/raw_data` | diverged copies | **abcdYi** | frozen (JP-S2-2) |
| Alembic base chain | shared `f66f720908c0` → `a1b2c3d4e5f6`, then forked; **revision id `b2c3d4e5f6a7` reused with different content in each repo** | same base, JP tail | shared history: **abcdYi**; JP tail: **Giraffe-JP** | never share one `alembic_version`; no history rewrite; new revisions use unique ids — REVIEW_REQUIRED |
| BM DB CI harness (root scripts) | present, CI-referenced | present, CI-referenced | duplicated tooling | KEEP both this stage; dedupe candidate for Stage 2 |

## Stage 2 handoff items

| Id | Item | Canonical destination |
|---|---|---|
| JP-S2-1 | Replace vendored `libs/GLTG` + local lead-time modules in Giraffe-JP with the fail-closed GLTG HTTP client pattern | GLTG external service |
| JP-S2-2 | Execute Option A: Giraffe-JP depends on pinned abcdYi package; remove frozen copied backend from JP, keep `src/giraffe_jp/*` + JP routes + JP migrations | abcdYi package |
| JP-S2-3 | Deduplicate BM DB CI harness scripts across repos | TBD (REVIEW_REQUIRED) |
| JP-S2-4 | Tenant-scope parity check (`src/db/tenant_scope.py`) | abcdYi |
| S2-5 | Evaluate converging backend and AIVAN-component shared DTO/client code into one internal library without breaking standalone AIVAN deployment | abcdYi |

## Rules applied

- No wholesale directory copying between repos in Stage 1 (PRD §12.2, §12.16).
- Code in the wrong repo is documented with its canonical destination, not moved (PRD §15).
- Unclear ownership → REVIEW_REQUIRED, code preserved.
