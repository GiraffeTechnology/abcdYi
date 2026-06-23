# GPM Public / Private Data Mode

## Overview

GPM (Giraffe Pricing Model) is shared between public and private deployments.
The difference between public mode and private mode is the **data source**, not the analysis architecture.

---

## Data Modes

| Mode | Data Sources |
|------|-------------|
| `public` | Authorized 1688 / Alibaba / marketplace APIs; CSV / Excel benchmark imports; public benchmark cache; non-customer public price evidence. |
| `private` | Customer ERP; historical supplier quotes; past purchase orders; internal supplier memory; private procurement records. |
| `mixed` | Both public and private sources within a single context bundle. |
| `mock` | Deterministic in-memory fixtures for testing and offline development. |

---

## Architecture: Same Core, Different Data Sources

Both public and private modes use the same analysis pipeline:

```
Data source
  ↓
evidence references (GPMEvidenceReference)
  ↓
GPMContextBundle
  ↓
Local Qwen reads retrieved context at inference time
  ↓
Schema-validated QwenSemanticAnalysis output
  ↓
Deterministic benchmark engine (BenchmarkEngine)
  ↓
Deterministic quote guidance engine (QuoteGuidanceEngine)
  ↓
GPMQuoteGuidance  →  human approval required
```

---

## Persistent Memory: DB/RAG, Not Model Weights

GPM does **not** train on customer data by default.

- Customer data remains in a customer-controlled data layer.
- Local Qwen reads retrieved context at inference time.
- Persistent memory is implemented through DB / store / RAG, not silent model weight updates.
- Fine-tuning is optional, explicit, offline, and requires separate approval.

---

## Security Guarantees

- Evidence references must not contain credentials (passwords, API keys, tokens).
- Context bundles exclude raw private data by default (payload excerpts only).
- Qwen output is schema-validated; invented prices, MOQ, or supplier IDs are rejected.
- All quote guidance retains `human_approval_required = True`.
- Automatic buyer-facing quote dispatch is not permitted.

---

## Local Qwen Boundary

The GPM Qwen runtime:

- Runs locally (MNN or mock).
- Does **not** call DashScope, Qwen cloud, OpenAI, Anthropic, DeepSeek, Gemini, or any external LLM API.
- Does **not** silently learn from pricing data passed at inference time.
- Returns schema-locked JSON only.

---

## Fine-Tuning

Fine-tuning is **not** implemented in GPM Core. It is:

- Future optional work.
- Explicitly scoped, offline, and requiring separate approval.
- Never automatic or implicit.
