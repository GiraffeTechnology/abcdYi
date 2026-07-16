# Final Code Governance Report — abcdYi (Stage 1)

- Base commit audited: `574d28c` (main).
- Work branch: `refactor/stage1-python311-code-governance-clean`.
- Scope executed: read-only audit → Python 3.11 restore → dependency/metadata
  reconciliation → documentation governance → product-level and test-suite
  validation.

## Product boundary

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

abcdYi ships the AIVAN runtime (`src/aivan`), CLI (`aivan`), web frontend
(`aivan serve`, :8765), smoke/contract/E2E scripts, and the OpenClaw channel
plugin as part of the standard product. The OpenClaw HTTP boundary is one
channel entry among several (web UI, CLI, IM/email adapters) — not the only
standard entry.

## What changed

1. **Python `>=3.11` restored** — pyproject was the only 3.9 holdout; CI,
   Docker and the committed lockfile already targeted 3.11. The 3.9-only
   `eval-type-backport` shim was removed. Lockfile rebuilt from scratch
   (the old lock was stale and contained a never-declared `gltg` entry).
2. **Dependencies reconciled on full-tree evidence** (backend + AIVAN + CLI +
   plugin + scripts + tests + CI): removed `aiosqlite` and `structlog`
   (unused); kept `jinja2` (AIVAN web templates), `python-dotenv` (AIVAN CLI),
   `python-multipart` (backend OAuth2 form login); merged the conflicting
   double dev-dependency declaration.
3. **Documentation made truthful**: 16 historical session/validation reports
   archived under `docs/archive/` with ARCHIVED banners; unread env vars
   removed from `.env.example`; README now lists AIVAN in the system boundary
   and documents both deployment modes; CHANGELOG header names the product.
4. **Product-level validation added**: integrated entry smoke, AIVAN→abcdYi
   workflow E2E, marketplace E2E, and OpenClaw plugin smoke against a live
   AIVAN server (see TEST_BASELINE_REPORT.md). The plugin smoke's stale action
   allowlist was extended with the runtime's documented safety-gate actions.

## Acceptance checklist

- [x] Python `>=3.11`; 3.9 shim removed
- [x] Clean 3.11 install from empty env; compileall PASS
- [x] AIVAN retained in the abcdYi product delivery (runtime, CLI, web, plugin, tests)
- [x] Integrated deployment verified: install → `aivan serve` → natural-language task → abcdYi workflow → approval-gated response
- [x] Standalone compatibility verified: OpenClaw plugin smoke over the stable AIVAN HTTP API (:8765)
- [x] Dependencies re-audited on the full tree (AIVAN included)
- [x] Ownership documentation correct and consistent across both repos
- [x] Migration up/down/up PASS (fresh PostgreSQL 16)
- [x] AIVAN → abcdYi E2E PASS (`scripts/run_aivan_e2e.py`)
- [x] Full suite 5× consecutive: 1078 passed / 7 skipped each run
- [x] Wheel build PASS
- [x] Safety invariants unchanged (human approval, tenant isolation, role
      switching, append-only events, replay protection, no silent fallback,
      no automatic external LLM call, no automatic order/payment/dispatch,
      fail-closed production auth, private-domain data boundary, human
      commercial/legal responsibility)

## Explicitly not done (with reasons)

- No product code was deleted: code-mass reduction is not the KPI; the only
  removals were unused dependencies, unread env-var documentation, and report
  archival.
- Backend↔AIVAN shared DTO/client convergence: REVIEW_REQUIRED for a later
  stage (must not break standalone AIVAN deployment).
- BM DB CI harness remains at repo root (CI references it by path) — Stage 2.
- Alembic revision-id collision with Giraffe-JP documented, not rewritten.
- `scripts/run_aivan_private_domain_rfq_e2e.py` requires the live GLTG
  service (its AIVAN-side GLTG API surface differs from the abcdYi CI mock);
  classified live/external in the test baseline.

## Deliverables

`docs/code-governance/`: STAGE1_ABCDYI_AUDIT.md,
STAGE1_CROSS_REPO_OWNERSHIP_MATRIX.md, PYTHON311_MIGRATION_REPORT.md,
DEPENDENCY_USAGE_REPORT.md, ENVIRONMENT_VARIABLE_MATRIX.md,
MIGRATION_INTEGRITY_REPORT.md, DEAD_CODE_REMOVAL_REPORT.md,
TEST_BASELINE_REPORT.md, this report.
