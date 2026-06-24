# GPM Operator API Service

Session F exposes the data-backed GPM quote guidance engine (Sessions A–E) as an
HTTP service callable by operators, OpenClaw skills, and internal gateways.

## Service Flow

```
Operator / OpenClaw / Gateway
  → POST /api/gpm/quote-guidance
  → GPMQuoteGuidanceApiService (wraps GPMSemanticQuoteService)
  → MockContextRetriever (default) or GiraffeDBContextRetriever
  → QwenLocalRuntime (mock | mnn | llm_api | auto)
  → GPMQuoteGuidancePacket (always pending, human_approval_required: true)
  → POST .../approve or .../reject  (operator records decision; no auto-dispatch)
  → best-effort audit writeback to giraffe-db /execution-events
```

## Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/api/gpm/healthz` | 200 | Service health |
| GET | `/api/gpm/capabilities` | 200 | Capabilities and constraints |
| POST | `/api/gpm/quote-guidance` | 201 | Generate quote guidance packet |
| GET | `/api/gpm/quote-guidance/{packet_id}` | 200/404 | Retrieve packet |
| POST | `/api/gpm/quote-guidance/{packet_id}/approve` | 200/404/409 | Record approval |
| POST | `/api/gpm/quote-guidance/{packet_id}/reject` | 200/404/409 | Record rejection |

## Error Codes

| Code | Meaning |
|------|---------|
| 201 | Packet created |
| 404 | Packet not found |
| 409 | Packet not in `pending` state |
| 422 | Insufficient data for guidance |
| 502 | giraffe-db context retriever unavailable |
| 503 | LLM runtime unavailable |

## Packet Contract (`GPMQuoteGuidancePacket`)

```python
packet_id: str               # e.g. "gpm_pkt_a1b2c3d4e5f6"
tenant_id: str | None
project_id: str | None
rfq_id: str | None
supplier_response_id: str | None
context_bundle_id: str | None
evidence_ids: list[str]
supplier_quote_position: str  # e.g. "above_benchmark"
recommendation: str
benchmark_range: dict
negotiation_points: list[str]
buyer_quote_options: list[dict]
runtime_profile: str           # local | ci | lightweight | server
runtime_mode: str              # mock | mnn | llm_api | auto
context_retriever: str         # mock | giraffe_db
data_mode: str                 # public | private
human_approval_required: True  # ALWAYS True — enforced in __post_init__
operator_action_required: bool
approval_status: str           # pending | approved | rejected | expired | superseded
audit_ref: str | None
created_at: str                # ISO-8601 UTC
```

## Hard Constraints

- `human_approval_required` is always `True` — enforced by `GPMQuoteGuidancePacket.__post_init__`
- Approve/reject endpoints record operator intent only; **no external actions are taken**
- No live 1688 API calls or scrapers
- No QC routes, models, or data
- No abcdYi DB migrations (packet store is in-memory)
- API keys are never logged; passed in headers only
- abcdYi calls giraffe-db via HTTP boundary only (`GiraffeDBClient`)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GPM_CONTEXT_RETRIEVER` | `mock` | `mock` or `giraffe_db` |
| `GPM_RUNTIME_PROFILE` | `local` | `local`, `ci`, `lightweight`, `server` |
| `GPM_LLM_RUNTIME_MODE` | profile-derived | `mock`, `mnn`, `llm_api`, `auto` |
| `GPM_GIRAFFE_DB_BASE_URL` | — | Required when `GPM_CONTEXT_RETRIEVER=giraffe_db` |
| `GPM_GIRAFFE_DB_API_KEY` | — | Optional audit-writeback key; never logged |

For `giraffe_db` context retrieval, also set the standard `GiraffeDBContextRetriever` vars
(`GPM_GIRAFFE_DB_BASE_URL`, tenant/operator headers).

## OpenClaw Skill

See `skills/gpm-quote-guidance/`. The skill calls `/api/gpm/quote-guidance` to request
guidance and exposes separate `approve` and `reject` actions. It never calls giraffe-db
or the Qwen runtime directly.

```typescript
const client = new GPMApiClient({ gpmApiBaseUrl: "http://localhost:8000" });
const resp = await client.createQuoteGuidance({ rfq_id: "rfq-001", operator_id: "op-1" });
// resp.packet.human_approval_required === true
// resp.packet.approval_status === "pending"
const approval = await client.approveQuoteGuidance(resp.packet.packet_id, {
  operator_id: "op-1", approval_note: "Approved after review",
});
// approval.dispatched === false  — no auto-dispatch ever
```

## Audit Writeback

Approval and guidance-creation events are written to giraffe-db `/execution-events`
on a best-effort basis. Failures are logged at `DEBUG` and do not affect API responses.
