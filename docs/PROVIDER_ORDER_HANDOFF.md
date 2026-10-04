# Provider-confirmed order consumer

## Scope and acceptance mapping

This implements the bounded AC-2 source handoff into the existing AC-3 execution
model. AC-4 evidence remains separate: local regression, actual provider/API
calls, model output, and full user workflow acceptance are different claims.
No supplier message, buyer commitment, new contract, signature, payment, or
production-host change is performed by this API.

## Configuration

- `ABCDYI_PRIVATE_DATA_PROVIDER_ID`: stable logical identity for the selected
  private provider. A compatible customer-owned provider is supported. Repointing
  a migrated endpoint does not mean changing the logical provider identity.
- `GIRAFFE_DB_BASE_URL` and `GIRAFFE_DB_SERVICE_AUTH_SECRET`: the existing provider
  configuration names; use the same selected provider as Aivan. The consumer
  calls its HTTP API only and does not import its source or access its DB tables.
- `ABCDYI_PRIVATE_DATA_TENANT_MAP`: optional server-owned JSON object mapping local
  authenticated tenant UUIDs to provider tenant IDs. Values must be unique.
  When this variable is absent, tenant IDs must be identical in both services.
  When present, an unmapped tenant fails closed. Request data cannot override it.
- `GLTG_SERVICE_AUTH_SECRET`: required for embedded Aivan's GLTG v2 client. It
  sends `X-Service-Auth` and `X-Service-Tenant-ID`; the payload tenant is the
  server-resolved service tenant. Production forbids test transport substitution.
- `GPM_GIRAFFE_DB_SERVICE_AUTH_SECRET`: the GPM context client's service secret,
  falling back to `GIRAFFE_DB_SERVICE_AUTH_SECRET`. The legacy
  `GPM_GIRAFFE_DB_API_KEY` Bearer value is not a substitute for provider service
  authentication. Per-request tenant headers cannot conflict with a fixed client
  tenant, and context response ownership is checked.

Apply `alembic upgrade head` through the installation/upgrade process before
serving the new API. The additive migration creates `provider_order_associations`.
Keep signing and service secrets out of frontend assets, logs, and source files.

## Import API

Send an authenticated `POST /api/orders/from-provider-confirmed` with JSON:

```json
{"purchase_order_id": "the-existing-provider-confirmed-po-id"}
```

The body accepts only that source identifier. The response is the existing
`OrderOut`, with stable local order/project IDs. A repeat import returns the same
order and its current execution state. A confirmed source can proceed to
production without an additional formal-contract state.

The selected provider must implement these tenant-bound HTTP contracts:

- `GET /api/data/purchase-orders/{po_id}`: confirmed PO with tenant ID, immutable
  confirmed requirement/quote snapshots, human authorization, confirmation time,
  and verified `source_snapshot_hash`
- `GET /api/data/purchase-orders/{po_id}/execution-state`: current revision,
  source hash, and optional association
- `POST /api/data/purchase-orders/{po_id}/execution-state`: compare-and-set write
  using `expected_revision` and the `abcdYi.execution.v1` association envelope

Requests carry `X-Service-Auth` and `X-Service-Tenant-ID`. Redirects are not
followed. Foreign records, source changes, association identity conflicts,
missing authorization, unconfirmed sources, incomplete price/requirements,
invalid provider replies, and uncertain readback do not launch an execution
order. Provider errors surface as stable codes without returning response bodies
or credentials to the caller.

The source must already satisfy the shared canonical-English provider contract.
Aivan's requirement `language` field records the detected source language and
may remain non-English after translation; it is not a business-content language
gate. The provider still validates the actual canonical business content.
The consumer does not convert text, synthesize missing business terms, or treat
an English label as proof of translation. Company and user profile handling is
unchanged. The association contains canonical English prose and technical
identities; it does not bypass the provider's business-language validator.

## Persistence boundary

The provider owns the confirmed business source and its bounded import
association. The existing abcdYi execution database owns later execution facts.
All imported records and the import audit event commit in one local transaction.
The authenticated actor initiating the import is distinct from the original
approval actor and confirmation time in the preserved source evidence.

Replay reconciles the existing provider association and does not overwrite
progressed local state. It can finish an initial import after a local transaction
failure. Restart/reload with the same execution database recovers local progress.
This patch does not implement backup/recovery of all later execution records
from the provider association, synchronize every lifecycle event to the provider,
or claim that the full apparel order lifecycle was accepted end to end.

## Verification

Run the normal migrated PostgreSQL route/integration suite and the existing
unit suites. New regression files are:

- `tests/unit/test_dependency_service_identity.py`
- `tests/api/test_provider_order_handoff.py`

They cover service headers, tenant binding and mismatches, invalid credentials,
redacted dependency errors, approval/source rejection, durable readback,
concurrent/repeated import, lost provider replies, local rollback and retry,
existing QC progression, authentication, and source drift. The synthetic
consumer fixtures are authored in this repository; no private provider dataset
or cross-repository fixture is redistributed.

An actual HTTP validation must additionally run the selected provider, GLTG, GPM,
and language service at identified revisions. Keep missing model execution,
designated-dataset coverage, and full UI/business-workflow gaps explicit even
when component HTTP calls and local regression tests pass.
