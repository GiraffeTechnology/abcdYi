# Main Branch Validation After PR #10

## Branch & Commit

- **Branch**: `main`
- **Commit**: `db15fe75bbe0659f9bf7c9b9e7963184fa05b4e9` (`db15fe7`)
- **PR merged**: [#10 — Integrate canonical lead time model into B/M runtime](https://github.com/GiraffeTechnology/giraffe-agent/pull/10)
- **Validation date**: 2026-06-14

---

## Commands Run

```bash
git fetch origin
git checkout main
git pull origin main

git log --oneline --decorate -5

uv sync

uv run pytest

uv run python scripts/run_db_smoke_test.py
uv run python scripts/run_bm_e2e_mvp.py
uv run python scripts/run_role_switching_mvp.py
uv run python scripts/run_merchandiser_e2e_mvp.py
uv run python scripts/run_logistics_cainiao_like_api_mvp.py
uv run python scripts/run_integrated_post_confirmation_mvp.py

uv run pytest tests/test_lead_time_imports.py tests/test_lead_time_model.py tests/test_lead_time_path_enumerator.py tests/test_b_side_feasibility_uses_lead_time_model.py tests/test_m_side_rollup_lead_time_components.py -q

uv run python scripts/run_lead_time_model_demo.py

GIRAFFE_DB_MODE=off uv run python run_bm_e2e_with_db.py

uv run pytest tests/test_mside_role_switching.py -q

for i in 1 2 3 4 5; do
  echo "MAIN VALIDATION RUN $i/5"
  uv run pytest tests/test_lead_time_imports.py tests/test_lead_time_model.py tests/test_lead_time_path_enumerator.py tests/test_b_side_feasibility_uses_lead_time_model.py tests/test_m_side_rollup_lead_time_components.py -q || exit 1
  uv run python scripts/run_lead_time_model_demo.py || exit 1
  GIRAFFE_DB_MODE=off uv run python run_bm_e2e_with_db.py || exit 1
  uv run pytest tests/test_mside_role_switching.py -q || exit 1
done
```

---

## Test Results

### Full pytest suite

```
266 passed in 3.70s
```

### Script MVPs

| Script | Result |
|--------|--------|
| `run_db_smoke_test.py` | SMOKE TEST PASSED: All 7 steps completed successfully |
| `run_bm_e2e_mvp.py` | PASSED |
| `run_role_switching_mvp.py` | 79/79 checks passed — ROLE-SWITCHING MVP E2E COMPLETE |
| `run_merchandiser_e2e_mvp.py` | AI MERCHANDISER E2E COMPLETE: 47 passed, 0 failed |
| `run_logistics_cainiao_like_api_mvp.py` | CAINIAO-LIKE LOGISTICS MVP COMPLETE: 54 passed, 0 failed |
| `run_integrated_post_confirmation_mvp.py` | INTEGRATED POST-CONFIRMATION MVP COMPLETE: 56 passed, 0 failed |

### Lead-time test suite (5 files)

```
114 passed in 0.23s
```

### Lead-time model demo

```
LEAD TIME MODEL DEMO: PASS

Summary (3 paths):
  rank=1 label=BEST_OVERALL supplier=Fabric Supplier A (Premium)    total= 14d slack=+16d risk_flags=0
  rank=2 label=FASTEST      supplier=Fabric Supplier B (Fast)       total= 12d slack=+18d risk_flags=0
  rank=3 label=LOWEST_COST  supplier=Fabric Supplier C (Substitute) total= 15d slack=+15d risk_flags=1
```

### BM E2E DB-off

```
[run_bm_e2e_with_db] PASS
```

### M-side role-switching tests

```
79 passed in 0.43s
```

---

## 5× Validation Loop

All 5 rounds completed with no failures.

| Round | Lead-time pytest (114) | Lead-time demo | BM E2E DB-off | Role-switching pytest (79) |
|-------|------------------------|----------------|---------------|---------------------------|
| 1/5 | 114 passed | PASS | PASS | 79 passed |
| 2/5 | 114 passed | PASS | PASS | 79 passed |
| 3/5 | 114 passed | PASS | PASS | 79 passed |
| 4/5 | 114 passed | PASS | PASS | 79 passed |
| 5/5 | 114 passed | PASS | PASS | 79 passed |

**Result: 5/5 rounds — ALL GREEN**

---

## Artifact Statement

No new runtime data artifacts were committed to `main` as a result of this merge. The `.gitignore` patterns introduced in PR #10 (and extended by PR #9) exclude all runtime-generated files under `data/b_side_workspaces/`, `data/m_side_workspaces/`, `data/projects/`, `data/order_execution/`, and related directories. Test runs during local validation produced workspace and project files with unique IDs; all were correctly excluded by `.gitignore` and none appear in `git status`.

## Final Statement

**`main` is clean after the PR #10 merge.** All 266 tests pass, all MVP scripts pass, the canonical Lead Time Path Model is fully operational, and no unintended files were introduced to the repository.
