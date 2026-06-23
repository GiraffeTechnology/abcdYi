# GPM Public / Private Data Mode

The `GPMContextBundle` supports four data modes that control which evidence categories are assembled for Qwen semantic analysis and benchmark computation.

## Data Modes

| Mode | Description | Use Case |
|---|---|---|
| `mock` | Deterministic synthetic data | CI, unit tests, smoke tests |
| `public` | Only public market evidence (1688, public APIs) | Default server mode without private data consent |
| `private` | Full context including private order history | Operator-enabled with tenant consent |
| `mixed` | Public + partial private, controlled by retriever | Configurable per-tenant |

## Privacy Rules

1. **Default is public**: `include_private_data=False` in all service calls unless operator explicitly enables it.
2. **Private data requires consent**: Private order history, supplier pricing history, and ERP data are only included when `include_private_data=True` is passed by an authorized operator path.
3. **No credentials in bundles**: `ContextBundleValidator` rejects any bundle containing credential-looking keys (`password`, `token`, `api_key`, etc.).
4. **Qwen never sees raw credentials**: `GPMContextBundle.to_prompt_payload()` strips credential-looking keys from evidence excerpts before building the prompt.

## GPMSemanticQuoteService

The Session D main service accepts `include_private_data` as an explicit parameter:

```python
output = service.run(
    tenant_id="t_123",
    rfq_id="rfq_456",
    include_private_data=False,  # default: public data only
)
```

With private data enabled (operator-authorized path only):

```python
output = service.run(
    tenant_id="t_123",
    rfq_id="rfq_456",
    include_private_data=True,  # requires operator authorization
)
```

## Mock Mode

In `mock` mode, the `MockContextRetriever` returns a synthetic context bundle with:
- 20 canonical price samples (men's cotton shirt, 24.0→46.04 CNY range)
- No real supplier identities
- No private tenant data
- `data_mode="mock"`

The mock scenario is deterministic: P50 ≈ 35.02, P75 ≈ 40.53, supplier quote 38.5 CNY → `within_high_range` → `negotiate`.

## Evidence Grounding

All evidence cited in Qwen output must be grounded in the context bundle:

```text
QwenOutputValidator checks:
  every evidence_id in output must exist in bundle.evidence_ids()
  hallucinated IDs are rejected with QwenOutputValidationError
```

## Human Approval Required

Regardless of data mode, `human_approval_required` is always `True` in all service output. No business action (quote dispatch, order, payment) may be taken automatically.
