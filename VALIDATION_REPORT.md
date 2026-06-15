# abcdYi Validation Report

## Product Positioning Fix

- Repositioned from C2M to B2M across README, PATENT_NOTICE.md, docs/product_scope.md, docs/patent_alignment_matrix.md, docs/user_manual.md, docs/release_notes_v1.md, docs/acceptance_criteria_v1.md, docs/final_status_report.md, docs/product_scope_v1.md, src/legal/patent_notice.py.
- Removed blockchain, virtual fitting, AR, and VR references from README and all primary product docs.
- Official patent titles preserved unchanged as registered legal titles.
- Added "Why B2M" section; added core user statement ("not an end consumer").
- Clarification added in README and PATENT_NOTICE.md: official patent titles retain C2M as registered legal titles; abcdYi product implementation is B2M.
- Dockerfile.api fixed: copies libs/GLTG before uv sync.
- scripts/run_clean_db_validation.sh updated to 8-step validation (including separate unit and integration test runs).
- Makefile updated: test-unit, test-integration, validate, docker-validate targets.

## Test Organisation Fix

- Moved `tests/unit/test_migrations.py` (DB-dependent) to `tests/integration/test_migrations.py`.
- Both migration tests marked `@pytest.mark.integration`.
- Added `delivery_feasibility_packets` to expected tables list.
- Registered `integration` marker in `[tool.pytest.ini_options]` in `pyproject.toml`.
- Unit test command: `uv run pytest tests/unit/ -v -m "not integration"` — runs without any database.
- Integration test command: `uv run pytest tests/integration/ -v` — requires migrated PostgreSQL.

---

## Validation Runs

### Run 1

Command:
```bash
uv run pytest tests/unit/ -v -m "not integration"
```

Result:
```
platform linux -- Python 3.11.15, pytest-9.1.0
collected 50 items

tests/unit/test_decision_packet_uses_gltg.py::test_gltg_enrichment_keys_present_in_lead_time_breakdown PASSED
tests/unit/test_decision_packet_uses_gltg.py::test_gltg_total_lt_preferred_over_calculator_result PASSED
tests/unit/test_decision_packet_uses_gltg.py::test_gltg_fallback_when_participant_not_in_gltg_results PASSED
tests/unit/test_decision_packet_uses_gltg.py::test_zero_options_gltg_packet_explanation_non_empty PASSED
tests/unit/test_delay_predictor.py::test_on_track_when_no_delays PASSED
tests/unit/test_delay_predictor.py::test_high_risk_when_8_days_late PASSED
tests/unit/test_delay_predictor.py::test_critical_when_more_than_14_days_late PASSED
tests/unit/test_delay_predictor.py::test_medium_risk_5_days_late PASSED
tests/unit/test_delay_predictor.py::test_no_milestones_returns_on_track PASSED
tests/unit/test_delay_predictor.py::test_low_confidence_when_no_predicted_dates PASSED
tests/unit/test_delay_predictor.py::test_delayed_milestones_listed PASSED
tests/unit/test_delivery_feasibility_service.py::test_path_to_dict_serialises_dates PASSED
tests/unit/test_delivery_feasibility_service.py::test_path_to_dict_none_dates_remain_none PASSED
tests/unit/test_delivery_feasibility_service.py::test_packet_to_dict_includes_ranked_options PASSED
tests/unit/test_delivery_feasibility_service.py::test_service_evaluate_persists_record_and_emits_event PASSED
tests/unit/test_delivery_feasibility_service.py::test_service_evaluate_raises_404_when_order_not_found PASSED
tests/unit/test_delivery_feasibility_service.py::test_service_evaluate_stores_gltg_feasibility_fields PASSED
tests/unit/test_gltg_adapter.py::test_evaluate_feasibility_returns_packet_with_ranked_options PASSED
tests/unit/test_gltg_adapter.py::test_evaluate_feasibility_no_participants_returns_incomplete PASSED
tests/unit/test_gltg_adapter.py::test_evaluate_feasibility_missing_sequential_returns_infeasible_path PASSED
tests/unit/test_gltg_adapter.py::test_evaluate_feasibility_deadline_comparison PASSED
tests/unit/test_gltg_adapter.py::test_evaluate_feasibility_never_fakes_options PASSED
tests/unit/test_gltg_adapter.py::test_evaluate_feasibility_multiple_manufacturers_up_to_3 PASSED
tests/unit/test_gltg_adapter.py::test_ranked_options_sorted_by_rank_score_descending PASSED
tests/unit/test_gltg_adapter.py::test_evaluate_feasibility_high_risk_node_flags PASSED
tests/unit/test_lead_time_calculator.py::test_parallel_stages_take_maximum PASSED
tests/unit/test_lead_time_calculator.py::test_missing_value_returns_none_not_sentinel PASSED
tests/unit/test_lead_time_calculator.py::test_sequential_stages_are_summed PASSED
tests/unit/test_lead_time_calculator.py::test_no_sentinel_values PASSED
tests/unit/test_lead_time_calculator.py::test_missing_fields_listed PASSED
tests/unit/test_lead_time_calculator.py::test_risk_flag_added_for_missing PASSED
tests/unit/test_lead_time_calculator.py::test_complete_calculation PASSED
tests/unit/test_lead_time_calculator.py::test_multiple_packets_aggregate PASSED
tests/unit/test_requirement_extraction.py::test_stub_extraction_marks_ai_generated PASSED
tests/unit/test_requirement_extraction.py::test_detect_missing_required_fields PASSED
tests/unit/test_requirement_extraction.py::test_generate_clarification_questions PASSED
tests/unit/test_scorer.py::test_score_returns_all_dimensions PASSED
tests/unit/test_scorer.py::test_no_history_defaults_to_neutral PASSED
tests/unit/test_scorer.py::test_category_fit_exact_match PASSED
tests/unit/test_scorer.py::test_category_fit_no_match PASSED
tests/unit/test_scorer.py::test_moq_fit_passes PASSED
tests/unit/test_scorer.py::test_moq_fit_fails PASSED
tests/unit/test_scorer.py::test_quality_history_from_memory PASSED
tests/unit/test_scorer.py::test_risk_penalty_applied_when_issues PASSED
tests/unit/test_scorer.py::test_compute_risk_flags_no_history PASSED
tests/unit/test_scorer.py::test_compute_risk_flags_low_qc PASSED
tests/unit/test_scorer.py::test_compute_risk_flags_late_delivery PASSED
tests/unit/test_scorer.py::test_compute_risk_flags_approaching_threshold PASSED
tests/unit/test_scorer.py::test_compute_risk_flags_incomplete_profile PASSED
tests/unit/test_scorer.py::test_missing_data_tracked PASSED

50 passed, 2 warnings in 0.15s
```

### Run 2

Command:
```bash
uv run pytest tests/unit/ -q -m "not integration"
```

Result:
```
50 passed, 2 warnings in 0.10s
```

### Run 3

Command:
```bash
uv run pytest tests/unit/ -q -m "not integration"
```

Result:
```
50 passed, 2 warnings in 0.09s
```

---

## Validation Status

| Check | Status | Notes |
|---|---|---|
| Unit tests (50 tests, no DB) | **PASS** | 50/50 across all 3 runs |
| Integration tests (2 migration tests) | **NOT RUN** | Docker not available in this environment |
| Docker build | **NOT RUN** | Docker not available in this environment |
| Alembic migration | **NOT RUN** | Docker not available in this environment |
| API health check | **NOT RUN** | Docker not available in this environment |
| Full clean validation run 1 | **NOT RUN** | Docker not available in this environment |
| Full clean validation run 2 | **NOT RUN** | Docker not available in this environment |
| Full clean validation run 3 | **NOT RUN** | Docker not available in this environment |
| C2M grep clean (product-level) | **PASS** | No product-level C2M outside official patent titles |
| blockchain / virtual fitting grep | **PASS** | No forbidden terms in product positioning docs |

## Final Result

**Unit tests: PASS — 50/50, 0 failures, 3 consecutive runs.**

**Full Docker validation: PENDING** — The Docker daemon is not available in this remote execution environment. The `scripts/run_clean_db_validation.sh` script is ready and must be run in an environment with Docker to complete the full validation:

```bash
./scripts/run_clean_db_validation.sh
```

The script executes:
1. `docker compose down -v`
2. `docker compose build`
3. `docker compose up -d db`
4. `docker compose run --rm migrate`
5. `docker compose up -d api`
6. `curl -f http://localhost:8000/health`
7. `uv run pytest tests/unit/ -v -m "not integration"`
8. `uv run pytest tests/integration/ -v`

Do not mark the full validation as PASS until all 8 steps complete successfully across 3 consecutive runs in a Docker environment.
