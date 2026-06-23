# GPM Session A — Implementation Report

Date: 2026-06-23

---

## 1. Summary

Session A delivers the **data ingestion and audit foundation** for GPM Lightweight.
It builds a clean pipeline from authorized API calls to validated, auditable
`GPMSupplierPriceSample` records that Session B can consume for benchmark and quote
guidance.

No pricing decision engine was implemented. No external LLM API was called.
No web scraping was introduced.

---

## 2. Files Added

### Python package

```
src/gpm/__init__.py
src/gpm/adapters/__init__.py
src/gpm/adapters/pricing_data_adapter.py
src/gpm/adapters/mock_1688_adapter.py
src/gpm/adapters/real_1688_adapter.py
src/gpm/models/__init__.py
src/gpm/models/pricing_query.py
src/gpm/models/raw_api_response.py
src/gpm/models/supplier_price_sample.py
src/gpm/normalization/__init__.py
src/gpm/normalization/sample_validator.py
src/gpm/storage/__init__.py
src/gpm/storage/local_json_store.py
src/gpm/storage/pricing_sample_repository.py
```

### OpenClaw skill skeleton

```
skills/gpm-1688-pricing/SKILL.md
skills/gpm-1688-pricing/README.md
skills/gpm-1688-pricing/config.example.json
skills/gpm-1688-pricing/src/index.ts
skills/gpm-1688-pricing/src/tools/fetchPriceSamples.ts
```

### Probe script

```
scripts/gpm_1688_api_probe.py
```

### Data directories

```
data/gpm/raw_api_responses/
data/gpm/supplier_price_samples/
```

### Tests

```
tests/unit/gpm/__init__.py
tests/unit/gpm/test_required_fields.py
tests/unit/gpm/test_mock_1688_adapter.py
tests/unit/gpm/test_raw_response_store.py
tests/integration/gpm/__init__.py
tests/integration/gpm/test_gpm_api_data_mock_flow.py
```

---

## 3. Data Models Implemented

### PricingQuery

Input DTO for a pricing search request.

Required fields: `keyword`, `source_platform` (default `1688`), `max_samples` (default `50`).

Optional fields: `product_type`, `material`, `process_tags`, `target_quantity`,
`target_unit`, `region_filter`.

### GPMRawAPIResponse

Preserves the raw API evidence for auditability.

Required fields: `id`, `source_platform`, `api_endpoint`, `query_keyword`,
`query_payload`, `response_payload`, `response_hash`, `captured_at`, `request_status`.

The `response_hash` (SHA-256 of the serialized `response_payload`) enables deduplication
and change detection in future sessions.

### GPMSupplierPriceSample

Normalized per-offer sample record.

Key computed fields (set by `validate_sample`):
- `usable_for_benchmark`: `True` only when all required fields pass
- `usable_for_quote_guidance`: mirrors `usable_for_benchmark` in Session A
- `invalid_reasons`: list of failure codes

---

## 4. Adapter Design

### PricingDataAdapter (ABC)

Defines the contract for all pricing data sources:

```python
def search_price_samples(query) -> tuple[GPMRawAPIResponse, list[GPMSupplierPriceSample]]
def get_offer_detail(offer_id) -> dict
```

### Mock1688PricingAdapter

Returns 25 deterministic mock samples (22 valid + 3 invalid) for the canonical
`纯棉男士衬衫 OEM 定制` scenario.

Valid samples vary across: supplier_id, supplier_location, MOQ (100–30000 pieces),
price_min/max (CNY 19–75), ladder_prices, and SKU attributes.

Invalid samples cover the three mandatory exclusion cases:
- `sample_inv_001`: `supplier_id = None` → `missing_supplier_id`
- `sample_inv_002`: `moq = None` → `missing_moq`
- `sample_inv_003`: `captured_at = None` and `observed_at = None` → `missing_observed_time`

### Real1688PricingAdapter

Stub. Raises `RuntimeError` unless `GPM_ENABLE_LIVE_1688_TESTS=true`.
Raises `EnvironmentError` if credentials are missing in live mode.
Does not log `APP_SECRET` or `ACCESS_TOKEN`.
Does not hardcode any credential.

---

## 5. Mock Adapter Result

```
GPM 1688 API PROBE: PASS
raw_response_id: raw_<uuid>
sample_count: 25
valid_sample_count: 22
invalid_sample_count: 3
invalid_reasons:
  missing_moq: 1
  missing_observed_time: 1
  missing_supplier_id: 1
```

---

## 6. Required-Field Validation Result

| Rule | Missing field | invalid_reasons code | Result |
|------|---------------|----------------------|--------|
| supplier_id is None | supplier_id | missing_supplier_id | excluded |
| moq is None | moq | missing_moq | excluded |
| captured_at and observed_at both None | both time fields | missing_observed_time | excluded |
| price_min is None and ladder_prices is empty | price | missing_price | excluded |
| All fields present | — | [] | usable_for_benchmark = True |

All five unit tests pass.

---

## 7. OpenClaw Skill Summary

Skeleton at `skills/gpm-1688-pricing/`:

- `SKILL.md`: Declares constraints (no scraping, no orders, no payments, no LLM API calls),
  required benchmark fields, and Session A tool contract.
- `src/index.ts`: Exports `tools.fetch_price_samples`.
- `src/tools/fetchPriceSamples.ts`: TypeScript skeleton; TypeScript-to-Python backend wiring
  is deferred to a future integration PR, not Session B.
- `config.example.json`: Documents the five required environment variables.

---

## 8. Test Results

### Unit Tests

| File | Tests | Status |
|------|-------|--------|
| `tests/unit/gpm/test_required_fields.py` | 5 | PASS |
| `tests/unit/gpm/test_mock_1688_adapter.py` | 4 | PASS |
| `tests/unit/gpm/test_raw_response_store.py` | 4 | PASS |

### Integration Test

| File | Tests | Status |
|------|-------|--------|
| `tests/integration/gpm/test_gpm_api_data_mock_flow.py` | 1 | PASS |

All 14 tests pass. No external credentials required. No live API called.

---

## 9. Known Limitations

1. **Real 1688 adapter is a stub.** `Real1688PricingAdapter.search_price_samples` raises
   `NotImplementedError`. Live integration requires a 1688 Open Platform account and must
   be done in a separate session.

2. **Local JSON store is ephemeral.** Files written to `data/gpm/` are local only.
   Session B should migrate to the project’s primary SQLite/PostgreSQL store when
   production persistence is needed.

3. **No Qwen-MNN normalization.** Product titles, material strings, and process tags
   are stored verbatim from the API. Semantic normalization is Session B scope.

4. **TypeScript skill is not wired to Python backend.** `fetchPriceSamples` throws
   `NotImplementedError`. TypeScript-to-Python backend wiring is deferred to a future
   integration PR. Session B is responsible for Qwen normalization, benchmark engine,
   and quote guidance engine only.

5. **No benchmark price range calculation.** Session A only collects and validates samples.
   Range computation is Session B scope.

---

## 10. Handoff Contract for Session B

Session B must consume:

| Asset | Location |
|-------|----------|
| `GPMSupplierPriceSample` | `src/gpm/models/supplier_price_sample.py` |
| `PricingQuery` | `src/gpm/models/pricing_query.py` |
| `Mock1688PricingAdapter` | `src/gpm/adapters/mock_1688_adapter.py` |
| `LocalJSONStore` | `src/gpm/storage/local_json_store.py` |
| Sample JSON files | `data/gpm/supplier_price_samples/*.json` |

Every valid sample exposes:

```
id
source_platform
supplier_id
captured_at or observed_at
product_title
price_min or ladder_prices
price_currency
price_unit
moq
moq_unit
raw_response_id
usable_for_benchmark
```

Session B must not need to know how the 1688 API was called.

Session B must not modify:

```
src/gpm/models/
src/gpm/normalization/
src/gpm/adapters/pricing_data_adapter.py
src/gpm/adapters/mock_1688_adapter.py
```

Session B may extend `PricingSampleRepository` and add a `real_1688_adapter` implementation.
