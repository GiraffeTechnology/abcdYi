# Stage 1 — Cross-Repo Ownership Matrix (abcdYi ↔ Giraffe-JP)

Audited at abcdYi `574d28c` / Giraffe-JP `41f24fb` (2026-07-16).
Measured duplication: Giraffe-JP `src/` = 326 files, of which 317 exist in abcdYi (175 byte-identical, 142 diverged forks).

| Capability | abcdYi | Giraffe-JP | Canonical owner | Action |
|---|---|---|---|---|
| AIVAN runtime | embedded copy at `src/aivan` (139 files, no production imports) | absent | **`aivan` repository** (external) | DELETE embed from abcdYi; consume via OpenClaw plugin HTTP boundary (:8765) |
| GLTG client | `src/integrations/gltg_client.py` (HTTP, fail-closed) — canonical pattern | vendored engine `libs/GLTG` + local `lead_time_calculator`/`path_enumerator` | **`GLTG` repository** (external service) | abcdYi: KEEP HTTP client. JP: KEEP vendored copy this stage with evidence; **Stage 2 handoff JP-S2-1**: migrate to HTTP client |
| GPM client/service | `src/gpm/` (single client set after aivan removal) | absent (no GPM surface) | **abcdYi** (`GPM` service external) | KEEP in abcdYi only |
| giraffe-db client | `src/gpm/clients/giraffe_db_client.py` | BM DB harness (`bm_db_adapter.py`, CI-only) | **`giraffe-db` repository** (external API) | one client boundary per repo; aivan duplicates deleted with embed |
| role switching | `src/actors`, `src/roles`, `api/routes/role_switching.py` | diverged copy of same modules | **abcdYi** | JP copy frozen; extraction to dependency = **Stage 2 handoff JP-S2-2** (Option A) |
| communication | `src/channels`, `src/order_confirmation` | diverged copy + `src/giraffe_jp/communication.py` (JP policy layer) | generic: **abcdYi**; JP auto-send/permission policy: **Giraffe-JP** | keep JP-specific layer in JP; generic copy frozen (JP-S2-2) |
| formalwear | `src/apparel_platform` (generic apparel) | `src/giraffe_jp/formalwear.py` + routes (C2B2M extension) | **Giraffe-JP** (JP business extension) | KEEP in JP |
| message permissions | `src/permissions` (generic) | diverged copy + `src/giraffe_jp/message_permissions.py` | generic: **abcdYi**; JP layer: **Giraffe-JP** | as communication |
| approval gates | `src/approval_gates` + `consumed_at` replay protection | diverged copy | **abcdYi** | JP copy frozen (JP-S2-2); replay-protection semantics must not diverge — REVIEW_REQUIRED on any future edit |
| tenant scope | `src/db/tenant_scope.py` (abcdYi only) + route-level filters | route-level filters only (no `tenant_scope.py`) | **abcdYi** | REVIEW_REQUIRED: confirm JP needs `tenant_scope.py` parity (Stage 2) |
| auth | `api/auth.py` (jose/passlib/OAuth2) | byte-similar copy | **abcdYi** | frozen copy (JP-S2-2) |
| execution events (append-only) | `src/execution_graph` | diverged copy | **abcdYi** | frozen copy; append-only invariant tests kept in both |
| OpenClaw plugin | `integrations/openclaw-aivan-plugin` (TS, HTTP) | `openclaw/skills` only | **abcdYi** (plugin), upstream OpenClaw external | KEEP; no Python-side duplicate after embed removal |
| API schemas | `api/routes/*` pydantic schemas | copy + 6 `giraffe_jp_*` route modules | shared: **abcdYi**; `giraffe_jp_*`: **Giraffe-JP** | frozen (JP-S2-2) |
| shared DTOs | `src/core_schema`, `src/raw_data` | diverged copies | **abcdYi** | frozen (JP-S2-2) |
| Alembic base chain | `f66f720908c0` → `a1b2c3d4e5f6` shared, then forked; **revision id `b2c3d4e5f6a7` reused with different content in each repo** | same base, JP-specific tail | shared history: **abcdYi**; JP tail: **Giraffe-JP** | never point both apps at one `alembic_version`; no history rewrite; new revisions must use unique ids — REVIEW_REQUIRED |
| BM DB CI harness (root scripts) | present, CI-referenced | present, CI-referenced | duplicated tooling | KEEP both this stage; dedupe candidate for Stage 2 |

## Stage 2 handoff items

| Id | Item | Canonical destination |
|---|---|---|
| JP-S2-1 | Replace vendored `libs/GLTG` + local lead-time modules with GLTG HTTP client (same fail-closed pattern as abcdYi `src/integrations/gltg_client.py`) | GLTG external service |
| JP-S2-2 | Execute Option A: Giraffe-JP depends on pinned abcdYi package; delete frozen copied backend from JP, keep `src/giraffe_jp/*` + JP routes + JP migrations | abcdYi package |
| JP-S2-3 | Deduplicate BM DB CI harness scripts across repos | TBD (REVIEW_REQUIRED) |
| JP-S2-4 | Tenant-scope parity check (`src/db/tenant_scope.py`) | abcdYi |

## Rules applied

- No wholesale directory copying between repos in Stage 1 (PRD §12.2, §12.16).
- Code in the wrong repo is documented with its canonical destination, not moved (PRD §15).
- Unclear ownership → REVIEW_REQUIRED, code preserved.
