# Apparel PRD closeout

This change implements the remaining apparel workflow and authorization gaps
against `Giraffe_Agent_MVP_v1.0_PRD.md` version 2.2. It does not change the product
scope, require contracts, add supplier/model counts, require production customer
data, or deploy any public service.

## Requirement and evidence map

| Requirement | Implementation and repeatable evidence |
| --- | --- |
| AC-1: canonical input and private business truth | `execution_language` validates typed records through the shared language API and dynamically normalizes non-English execution input before mutation. Unavailable translation fails without storing an original. Lineage records hashes. `test_execution_language_boundary.py` tests actual route persistence and missing-model rejection. |
| AC-2: approved quotation and confirmed order | `approval_binding` binds project, option, form revision, immutable payload hashes, human actor, role and time. Material changes and explicitly unresolved material fields cannot reuse approval. Provider import verifies the same confirmed requirement/quote and rejects unresolved flags. No contract/signature state is added. `test_commercial_binding.py` covers rejection, correction, stale versions and idempotency. |
| AC-3: production and QC | Tenant/project-scoped milestones preserve prior values in events. Failed QC remains immutable; an authorized recorded rework resolution permits reinspection. Empty inspection and missing/invalid numeric criteria cannot auto-pass. `test_execution_safety.py` exercises failure, repair, rollback and nested identity rejection. |
| AC-3: logistics and sign-off | Arrival alone does not imply final delivery. Carrier delivery leaves buyer sign-off pending. A separately authenticated buyer/proxy/admin signs off; supplier memory is derived only from scoped observed records and is idempotent. |
| AC-3: authoritative recovery | The selected compatible provider stores complete bounded lifecycle records through its existing CAS execution-state API. Every write requires exact readback; UTC wire timestamps are canonicalized. Reads and mutations refresh the SQL execution view. Lost replies, stale revisions, missing local records and a fresh execution DB are reconciled from provider history. |
| Participant confidentiality | Explicit project memberships separate internal buyer/procurement access from manufacturing, QC and logistics capabilities. Global roles or request headers cannot replace project grants. URL and nested body resource ownership are checked before workflow handlers. `test_project_membership.py` includes a single actor acting as buyer in one project and manufacturer in another. |
| AC-4: separate claims | Regression contracts, real dependency API execution and installable-package acceptance have separate evidence. The documented API workflow does not claim public deployment, external message delivery or successful model inference. |

## Provider durability and security

`provider_order_associations.execution_revision` and `execution_snapshot_hash`
record the verified provider revision. Lifecycle state includes order lines,
milestones, production observations, QC criteria/results, human dispositions,
shipments, tracking, sign-off, supplier memory and order event history. The
confirmed requirement is referenced by its immutable source hash instead of
being duplicated in every order-line snapshot. Recovery restores its exact
meaning from that source.

Both outgoing and recovered snapshots validate identity, commercial terms,
foreign-key scope and the QC/delivery/sign-off evidence chain. A hash alone is
not commercial or human authorization. Authentication identities and permission
grants remain separately provisioned security configuration; a business record
never creates credentials, users or roles during recovery.

A provider write can commit before a local SQL commit fails. The response then
remains failed; the next authenticated access reads the same provider revision
and repairs the local view. It never invents a second order or repeats a business
send. Provider outages and uncertain/mismatched readback fail visibly.

## Configuration and installation

Use the selected provider configuration and one-to-one tenant mapping documented
in `PROVIDER_ORDER_HANDOFF.md`. Apply both additive migrations before serving an
upgraded PostgreSQL installation. The complete offline installer manages the
execution service and its SQL view with the same provider and language services;
a component wheel alone is not the complete installation deliverable.

Execution text requires `AIVAN_LANGUAGE_SKILL_BASE_URL` or
`GIRAFFE_LANGUAGE_SKILL_URL`. English operation does not require translation
weights. A non-English request requires a functioning translation backend and
fails truthfully if one is unavailable. The explicit isolated-test bypass is
accepted only when `AIVAN_ENV=test`; it cannot disable production enforcement.

Project owners and tenant administrators can assign or revoke existing users via
`POST /api/projects/{project_id}/memberships` and
`DELETE /api/projects/{project_id}/memberships/{user_id}`. An execution collaborator
must name its tenant-owned participant. Membership does not generate credentials
or replace the persisted human role required for commercial/QC decisions.

## Verification commands

Run the complete migrated PostgreSQL suite, migration reversibility, the
configured frontend checks, and installed-runtime smoke tests for the final
candidate. Focused additions are:

```sh
pytest -q tests/api/test_commercial_binding.py tests/api/test_execution_safety.py \
  tests/api/test_provider_lifecycle_recovery.py tests/api/test_provider_recovery_adversarial.py \
  tests/api/test_project_membership.py tests/api/test_execution_language_boundary.py
```

Exact candidate SHAs, final counts, real-HTTP evidence and installer checksums are
recorded in the release/PR evidence after verification. Optional live-model skips
are not model execution; mocks are not real provider acceptance. No production
hosts, production records or external commercial communications were changed.
