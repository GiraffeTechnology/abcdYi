# Changelog

All notable changes to Giraffe Agent are recorded here.

---

## [BM_DB_INTEGRATION_BASELINE_V1] — 2026-06-13

### Tag
`BM_DB_INTEGRATION_BASELINE_V1`

### Classification
BM DB Integration Baseline v1 is a reproducible integration baseline, not yet a
production-hardening release.

### Summary
First fully reproducible B/M-side DB integration baseline.  The integration
package previously did not exist in a runnable form; five distinct failure modes
were identified and resolved.  The verifier now passes 5/5 runs with clean
PRAGMA checks against a fresh SQLite database.

### Added
- `pydantic_stub.py` — re-export shim so `import pydantic_stub` resolves;
  provides a minimal `BaseModel` fallback when pydantic is absent
- `build_schema.py` — schema builder using `GIRAFFE_DB_URL` / `--url`; no
  hard-coded paths; `create_all` idempotent against an existing DB
- `bm_db_adapter.py` — unified adapter with lazy `src.db.*` imports;
  `_mode=off` uses `_MemStore` (pure in-memory); `_mode=on` uses real
  SQLAlchemy repositories; `get_or_create_actor` and `get_or_create_project`
  for idempotency; `update_edge` back-fills `inquiry_id`, `response_id`, status
- `run_bm_e2e_with_db.py` — end-to-end runner; adds `sys.path` fixup; handles
  both `GIRAFFE_DB_MODE=off` and `GIRAFFE_DB_MODE=on`; auto-creates schema in
  on-mode
- `verify_integration.py` — reproducibility verifier; `--db` and `--runs` args;
  runs full 11-step lifecycle per iteration; asserts row counts for 8 tables;
  checks `procurement_edges.inquiry_id` and `.response_id` linkage; asserts
  `edge.status == APPROVED`; runs `PRAGMA integrity_check` and
  `PRAGMA foreign_key_check` at end
- `docs/BM_DB_INTEGRATION_BASELINE_v1.md` — full test report
- `TEST_RESULT.md` — machine-readable test result record

### Fixed
- `ModuleNotFoundError: pydantic_stub` — module now exists
- `ModuleNotFoundError: src` in `run_bm_e2e_with_db.py` — explicit
  `sys.path` fixup at script top
- Hard-coded absolute migration path in `build_schema.py` — replaced with
  `--url` / `GIRAFFE_DB_URL`
- `verify_integration.py` bypassed `bm_db_adapter.py` and wrote raw sqlite
  rows — verifier now goes exclusively through `BMDbAdapter`
- DB-off mode broken by module-level `src.db.*` imports in
  `bm_db_adapter.py` — all such imports are now lazy

### Changed
- `README.md` — E2E Verification section now includes the B/M-side DB
  Integration Baseline v1 block with commands, result, and link to report

### Verified
| Check | Result |
|-------|--------|
| `python -m py_compile *.py` | PASS |
| `GIRAFFE_DB_MODE=off python run_bm_e2e_with_db.py` | PASS |
| `GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py` | PASS |
| `python verify_integration.py --db sqlite:///./test.db --runs 5` | 5/5 PASS |
| `PRAGMA integrity_check` | ok |
| `PRAGMA foreign_key_check` | ok |

---

## [MVP v1.0] — 2026-05-26

Initial MVP release covering:

- AI Buyer (B-side): requirement structuring, bilingual inquiry drafting,
  delivery feasibility simulation
- Supplier Response Agent (M-side): intake, normalization,
  `SupplierResponsePacket`
- Role-Switching Procurement Agent: recursive `UPSTREAM_B_SIDE` logic,
  upstream inquiry builder, option engine, approval gate
- Professional Free CAD↔CNC Matching: `CADRequirementPacket`,
  `CapabilityFitReport`, machine profile matching (no encryption, no
  watermarking)
- AI Merchandiser: post-confirmation milestones, production/QC/exception
  updates, logistics handover, buyer sign-off
- Cainiao-like logistics ingestion: carrier API normalization, shipment
  tracking
- Database layer: SQLAlchemy 2.x models, Alembic, SQLite (local) /
  PostgreSQL-compatible schema
- Dynamic self-learning schema: observe → propose → approve field lifecycle
- Industrial Execution Graph v0.1: append-only `ExecutionEvent` log
- OpenClaw skill manifest, WeChat/WhatsApp/Web channel adapters
