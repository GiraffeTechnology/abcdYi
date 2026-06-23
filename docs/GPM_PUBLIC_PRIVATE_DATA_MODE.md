# GPM Public / Private Data Mode

## Summary

GPM Core is shared between public and private deployments. The difference between public and private mode is the data source, not the analysis architecture.

## Data Modes

### Public Mode

Public mode uses externally sourced market data:

- Authorized marketplace APIs (e.g. 1688 / Alibaba)
- CSV / Excel benchmark imports
- Public benchmark caches
- Non-customer public price evidence

### Private Mode

Private mode uses customer-controlled internal data:

- Customer ERP
- Historical supplier quotes
- Past purchase orders
- Internal supplier memory
- Private procurement records

## Shared Architecture

Both modes produce a `GPMContextBundle` and follow the same core flow:

```
Data source
→ evidence references (GPMEvidenceReference)
→ GPMContextBundle
→ local Qwen semantic analysis
→ deterministic benchmark + quote guidance engines
→ auditable GPMQuoteGuidance
```

## Persistent Memory

GPM does not train on customer data by default.

- Customer data remains in a customer-controlled data layer.
- Local Qwen reads retrieved context at inference time only.
- Persistent memory is implemented through DB / document store / RAG, not silent model weight updates.
- Fine-tuning is future optional explicit work requiring separate approval.

## Human Approval

Any buyer-facing quote dispatch requires explicit human approval (`human_approval_required = True`). Qwen is never permitted to authorize buyer-facing quote dispatch, place orders, or make payments.

## What GPM Does Not Do

- No external LLM API calls (no OpenAI, Anthropic, DashScope, Gemini, DeepSeek).
- No Qwen cloud calls.
- No silent model training on customer data.
- No automatic order placement.
- No automatic buyer quote dispatch.
