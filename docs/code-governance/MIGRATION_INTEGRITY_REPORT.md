# Migration Integrity Report — abcdYi (Stage 1)

## Backend migration graph

Linear chain, no branches, no merge points:

```
f66f720908c0  iter1_initial_schema
    └─ a1b2c3d4e5f6  add_delivery_feasibility_packets
        └─ b2c3d4e5f6a7  reconcile projects role-switching columns
            └─ c3d4e5f6a7b8  add approval_requests.consumed_at (replay protection)
```

## Validation (fresh PostgreSQL 16, empty database)

```
alembic upgrade head      PASS  (all 4 revisions applied)
alembic downgrade base    PASS  (clean teardown to empty)
alembic upgrade head      PASS  (re-applied from empty)
```

Existing-database upgrade: the primary test database was migrated to head and
the full suite (`tests/db/`, `tests/api/`, `tests/integration/`) passes
against it.

## AIVAN component store

The AIVAN component maintains its own local persistence (`AIVAN_DB_URL`,
sqlite by default; initialized via `aivan init` / `init_db()`), separate from
the backend's Alembic-managed PostgreSQL schema. This separation is
intentional: AIVAN must support standalone deployment. It is not part of the
backend migration chain and requires no Alembic revisions.

## Drift checks

- No duplicate tables/columns/indexes across revisions.
- Model/migration drift: `tests/db/` schema tests pass against `upgrade head`.
- No migration rewritten; Stage 1 added no revisions.

## Cross-repo hazard (documented, not fixed here)

Revision id `b2c3d4e5f6a7` exists in BOTH repos with different content
(abcdYi: role-switching column reconcile; Giraffe-JP: giraffe_jp service
core). The two applications must never share one `alembic_version` table,
and future revisions in either repo must use freshly generated ids.
Status: REVIEW_REQUIRED (Stage 2 cross-repo item; rewriting published
migration history is forbidden by PRD §9/§12.12).
