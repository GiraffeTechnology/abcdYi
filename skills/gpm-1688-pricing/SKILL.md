# GPM 1688 Pricing Skill

## Purpose

This skill retrieves authorized pricing data from 1688 / Alibaba pricing-data APIs.

## Constraints

- It does not scrape websites.
- It does not place orders.
- It does not make payments.
- It does not send buyer-facing quotes automatically.
- It does not call external LLM APIs.
- It requires supplier_id, captured_at / observed_at, and MOQ for every benchmark-eligible sample.

## Session A Tool

### fetch_price_samples

Retrieves authorized pricing samples from 1688 / Alibaba pricing-data APIs for a given keyword and quantity.

#### Input

```json
{
  "keyword": "纯棉男士衬衫 OEM 定制",
  "target_quantity": 10000,
  "target_unit": "piece",
  "max_samples": 50,
  "source_platform": "1688"
}
```

#### Output

```json
{
  "raw_response_id": "raw_abc123",
  "sample_count": 25,
  "valid_sample_count": 22,
  "invalid_sample_count": 3,
  "invalid_reasons": {
    "missing_supplier_id": 1,
    "missing_moq": 1,
    "missing_observed_time": 1
  },
  "sample_ids": ["sample_001", "sample_002"]
}
```

## Required Fields for Benchmark Eligibility

Every benchmark-eligible sample must have:

- `supplier_id` — identifies the supplier
- `captured_at` or `observed_at` — timestamp of price observation
- `moq` — minimum order quantity

Samples missing any of these fields are stored but flagged `usable_for_benchmark: false`.

## Not In Scope (Session A)

- Qwen-MNN semantic normalization
- Benchmark price range calculation
- Quote guidance
- Accept / negotiate / reject decision logic
- Buyer-facing quote options
- GLTG integration
- Cloud LLM API calls
- HTML scraping or browser automation
