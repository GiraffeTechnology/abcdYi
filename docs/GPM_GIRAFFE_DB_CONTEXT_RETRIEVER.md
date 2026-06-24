# GPM giraffe-db Context Retriever

Documentation for Session E: integrating the giraffe-db HTTP context retriever into the abcdYi GPM pipeline.

---

## Overview

The GPM (Global Procurement Management) pipeline in abcdYi needs procurement context—historical pricing, supplier quotes, RFQ data—to generate semantic quote guidance. Before Session E, this context was always sourced from a deterministic in-memory mock.

Session E introduces `GiraffeDBContextRetriever`, an HTTP-backed implementation that calls the giraffe-db persistence service to fetch real context bundles. The mock remains the CI-safe default.

---

## Architecture

```
                    abcdYi
                      ┌─────────────────────────────┐
                      │ GPMSemanticQuoteService  │
                      └─────────┬────────────────┘
                               │
                   ┌─────────┼─────────┐
                   │ GPMContextRetriever Protocol │
                   └────┬────────┬───────┘
                        │             │
            ┌─────────┴─┐   ┌───┴──────────────────┐
            │MockContext  │   │ GiraffeDBContextRetriever  │
            │Retriever    │   └───────┬─────────────────┘
            │(canonical)  │            │
            └─────────────┘    ┌──────┴──────┐
                           │GiraffeDBClient │
                           │  (httpx)       │
                           └──────┬───────┘
                                  │ HTTP
                           ┌──────┴──────┐
                           │  giraffe-db   │
                           │  FastAPI svc  │
                           └─────────────┘
```

---

## File Structure

```
src/gpm/
  clients/
    __init__.py
    giraffe_db_client.py       # httpx HTTP client
  context/
    mappers/
      __init__.py
      giraffe_db_context_mapper.py   # response → GPMContextBundle
    retrievers/
      __init__.py
      base.py                  # GPMContextRetriever Protocol
      mock_context_retriever.py     # new-namespace mock
      giraffe_db_context_retriever.py
      retriever_config.py      # env-driven factory
```

---

## Quick Start

### Mock mode (default, CI-safe)

```python
from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService

service = GPMSemanticQuoteService()  # builds MockContextRetriever from env
output = service.run()
```

### giraffe-db mode

```bash
export GPM_CONTEXT_RETRIEVER=giraffe_db
export GPM_GIRAFFE_DB_BASE_URL=http://localhost:8001
```

```python
from src.gpm.context.retrievers.retriever_config import build_context_retriever_from_env
from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService

retriever = build_context_retriever_from_env()
service = GPMSemanticQuoteService(context_retriever=retriever)
output = service.run(rfq_id="rfq_abc", tenant_id="tenant_001")
```

### Direct client usage

```python
from src.gpm.clients.giraffe_db_client import GiraffeDBClient
from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever

client = GiraffeDBClient(
    base_url="http://localhost:8001",
    tenant_id="tenant_001",
    api_key="your-api-key",  # never logged
)
retriever = GiraffeDBContextRetriever(client=client, default_tenant_id="tenant_001")
bundle = retriever.retrieve(rfq_id="rfq_001", include_private_data=False)
```

---

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GPM_CONTEXT_RETRIEVER` | `mock` | No | `mock` or `giraffe_db` |
| `GPM_GIRAFFE_DB_BASE_URL` | — | When `giraffe_db` | Base URL of giraffe-db service |
| `GPM_GIRAFFE_DB_TIMEOUT` | `30.0` | No | HTTP timeout in seconds |
| `GPM_GIRAFFE_DB_TENANT_ID` | — | No | Tenant ID for request header and payload |
| `GPM_GIRAFFE_DB_OPERATOR_ID` | — | No | Operator ID request header |
| `GPM_GIRAFFE_DB_API_KEY` | — | No | Bearer token (never logged) |
| `GPM_GIRAFFE_DB_INCLUDE_PRIVATE_DATA` | `false` | No | Include tenant-private records |

---

## Data Mode

`GPMContextBundle.data_mode` is set by the mapper based on which sources contributed data:

| Condition | `data_mode` |
|-----------|-------------|
| Only public evidence (pricing_evidence, imported_api_records) | `"public"` |
| Only private evidence (include_private_data=True, no public pricing) | `"private"` |
| Both public pricing + private evidence | `"mixed"` |
| Mock retriever | `"mock"` |

---

## Private Data

Private records (`private_data_records`, `private_customer_quote_history`) are **excluded by default**. Pass `include_private_data=True` to include them:

```python
bundle = retriever.retrieve(rfq_id="rfq_001", include_private_data=True)
```

Private records contribute to `bundle.evidence` only — they do not populate `bundle.price_samples` (their pricing is tenant-specific and not used for market benchmarking).

---

## Error Handling

When `GPM_CONTEXT_RETRIEVER=giraffe_db`, network failures raise `GiraffeDBClientError` — **there is no silent fallback to mock**. This is intentional: operators need to know immediately if giraffe-db is unreachable.

```python
from src.gpm.clients.giraffe_db_client import GiraffeDBClientError

try:
    bundle = retriever.retrieve(rfq_id="rfq_001")
except GiraffeDBClientError as e:
    # giraffe-db unreachable or returned an error HTTP status
    logger.error("GPM context retrieval failed: %s", e)
    raise
```

---

## Testing

Use `GiraffeDBClient(transport=...)` to inject an `httpx.BaseTransport` for test isolation:

```python
import httpx
from src.gpm.clients.giraffe_db_client import GiraffeDBClient
from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever

class MockTransport(httpx.BaseTransport):
    def handle_request(self, request):
        return httpx.Response(200, json=MY_TEST_RESPONSE)

client = GiraffeDBClient(base_url="http://test", transport=MockTransport())
retriever = GiraffeDBContextRetriever(client=client)
bundle = retriever.retrieve()
```

---

## Credential Safety

The mapper strips these keys from all `payload_excerpt` fields before they enter `GPMContextBundle.evidence`:

`password`, `passwd`, `token`, `api_key`, `apikey`, `secret`, `authorization`, `cookie`, `session`, `private_key`, `access_key`, `auth`, `bearer`, `credential`

API keys and bearer tokens are **never printed, logged, or included in exception messages** anywhere in the client or retriever.
