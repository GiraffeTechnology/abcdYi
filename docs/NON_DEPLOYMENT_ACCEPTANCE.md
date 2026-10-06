# Non-deployment acceptance and MyAivan handoff

## Scope and PRD mapping

- **AC-2:** The abcdYi web entry opens the configured MyAivan application, which
  owns inquiry, quotation, login, human commercial approval, and order confirmation.
  This is navigation integration, not a replacement Aivan workflow or proof of a
  deployed cross-application order handoff.
- **AC-3:** `POST /api/orders/{order_id}/request-qc` records the existing legal
  `IN_PRODUCTION` to `QC_PENDING` transition. It requires the authenticated user's
  tenant-owned order, locks that order for the transaction, and persists a
  `QC_REQUESTED` event with actor, tenant, project, order, prior state, and new state.
  Invalid/repeated requests return 409; unknown/foreign orders return 404. State
  and audit write commit together. The state model, QC outcome rules, shipping
  gate, buyer-sign-off requirement, and commercial approvals are unchanged.
- **AC-4:** The backend synthetic API regression, frontend entry checks, live
  dependency integration, and deployed user acceptance remain distinct claims.

No formal contract, signature, new order state, or fixed set of completed
milestones is introduced as a production or QC prerequisite. The synthetic
acceptance scenario records its applicable production milestones before requesting
QC; that scenario does not add a universal product gate.

## Same-provider confirmed-order handoff

`POST /api/orders/from-provider-confirmed` accepts a `purchase_order_id` under
abcdYi's normal JWT authentication. It reads the selected provider's confirmed
PO API, requires the Aivan-confirmed quote and requirement snapshots, verifies
tenant ownership and human authorization, and creates the existing apparel
execution records in `IN_PRODUCTION`. It adds no formal-contract prerequisite
and performs no new buyer approval or outbound supplier communication.

The provider is chosen by server configuration, never by request input. Its
service identity and tenant namespace must match the provider selected by Aivan.
The request cannot choose a URL, credential, tenant, project, or provider identity.
The optional operator-owned tenant mapping is one-to-one. Source PO, quote,
requirement, selected option, parties, approval evidence, confirmation time, and
source hash remain associated with the local execution order.

The provider's compare-and-set execution-state API stores a bounded import
association. A successful HTTP write alone is insufficient: authoritative
readback must match source hash, identities, tenant, and association. A lost
response is reconciled by reading the same PO. Deterministic IDs and the local
unique constraint prevent duplicate execution orders; a replay never resets
production, QC, shipping, or sign-off progress. The local execution transaction
persists its records and audit event together. If that transaction fails after
the remote association commits, retrying the same PO completes the local import.

The selected provider now owns both confirmation and complete in-scope apparel
lifecycle snapshots. The SQL execution database is a recoverable materialized
view. Real provider readback, CAS revisions, immutable commercial source checks,
QC/sign-off evidence validation and fresh-view recovery are covered by the
[PRD closeout implementation and evidence](PRD_CLOSEOUT_ACCEPTANCE.md). This does
not claim public deployment or external channel delivery. The frontend navigation
link alone still does not establish a completed business workflow.

## Backend regression

`scripts/run_v1_acceptance_apparel_order.py` now uses authenticated HTTP APIs for
all order-state changes, including QC handoff. It no longer imports the database
or sets order status directly. It checks persisted order readback at QC, shipment
readiness, delivery, and the final event chain. Carrier delivery must leave buyer
sign-off unset until the separate sign-off request.

The server has no public registration route. Provision a synthetic acceptance
account in the test environment using the existing operator process, then supply
`BASE_URL`, `ACCEPTANCE_EMAIL`, and `ACCEPTANCE_PASSWORD` through that environment's
approved configuration. Run:

```sh
uv run python scripts/run_v1_acceptance_apparel_order.py
```

Do not place test credentials in repository files or logs. Use an isolated test
tenant and synthetic records. Running this script changes test business records
and approves its synthetic proposals; it is not a read-only production probe.

The CI `API + Integration (Postgres)` job migrates PostgreSQL and runs the complete
route and integration suite, including this script through the actual ASGI app,
tenant/authentication rejection, invalid/repeated QC handoff, failure rollback,
persisted readback from a new client, and pass/fail shipping behavior. Its shared
GLTG fixture is a mock. Therefore a green result is backend regression evidence,
not evidence of live GLTG/GPM, MyAivan, external channel receipts, or the designated
simulated private-data providers.

## Frontend regression

`frontend` uses the operator-supplied `VITE_MYAIVAN_URL`. It shows a clear status
when the value is missing or invalid. It never invents a host/port, sends tokens,
embeds MyAivan in an iframe, or assumes cross-application SSO. MyAivan owns its
normal login and server-side tenant binding. The `MyAivan Entry` CI job runs
`npm ci`, `npm test`, and `npm run build`; the tests cover valid paths/ports,
unsafe or credential-bearing URLs, missing configuration, and repeatable rendering.

## Requirements for the deployment handoff

1. Select and record the exact merged abcdYi and Aivan revisions; confirm all CI
   checks for those exact heads before merging. An open/draft PR is not a release.
2. Confirm the approved, externally reachable MyAivan web entry, normally `/app`,
   and supply it as `VITE_MYAIVAN_URL` before starting the existing development
   server or building production static assets. Confirm any existing path-prefix
   routing and `/static` assets. Do not infer a new web allocation from these docs.
3. Use the deployment configuration for host/port assignments and preserve
   occupied service ports. No host, listener, TLS, firewall, credentials, or
   production data is changed by this work.
4. Configure MyAivan's existing authentication and tenant mapping and the selected
   replaceable private-data provider through their supported server-side settings.
   Never put deployment credentials or service API keys in the browser bundle.
5. Exercise the actual Aivan inquiry-to-quotation-to-confirmation flow and verify
   the confirmed-order handoff to abcdYi preserves tenant, project, order,
   requirement/quotation versions, selected option, parties, approval actor/time,
   and source references. A frontend link alone does not prove this handoff.
6. Execute the configured GLTG/GPM dependency APIs and the two designated simulated
   databases (or the selected compatible private provider). Synthetic provenance
   is valid acceptance data. Record actual calls, durable write/readback and
   restart/reload recovery, failures, and skips without substituting local mocks.
7. Verify human confirmation before every external commercial email, IM, or API
   send, including material changes. Internal dependency API analysis calls are
   separate from external commercial communications. Test the approved OpenClaw
   IM/email access paths and retain real channel receipts when exercised.
8. In the browser, verify MyAivan login, failed/interrupted login, retry, Back and
   repeated entry navigation, then the same confirmed apparel order through
   production, QC, shipping, delivered-but-not-accepted, buyer sign-off, and supplier
   performance evidence. Keep Stage 1 and full lifecycle evidence separate.

These are deployment acceptance instructions, not a claim that deployment or the
full multi-service acceptance has already run.
