# Migration Integrity Report — abcdYi (Stage 1)

## Migration graph

Linear chain, no branches, no merge points:

```
f66f720908c0  iter1_initial_schema
    └─ a1b2c3d4e5f6  add_delivery_feasibility_packets
        └─ b2c3d4e5f6a7  reconcile projects role-switching columns
            └─ c3d4e5f6a7b8  add approval_requests.consumed_at (replay protection)
```

## Validation (fresh PostgreSQL 16, empty database `mig_check_abcdyi`)

```
alembic upgrade head      PASS  (all 4 revisions applied)
alembic downgrade base    PASS  (clean teardown to empty)
alembic upgrade head      PASS  (re-applied from empty)
```

Existing-database upgrade: the primary test database (`apparel_textile`) was
migrated to head and the full suite (including `tests/db/`, `tests/api/`,
`tests/integration/`) passes against it.

## Drift checks

- No duplicate tables/columns/indexes across revisions (chain reviewed).
- Model/migration drift: `tests/db/` schema tests pass against `upgrade head`.
- `src/aivan/db` was a second, disconnected persistence layer inside the
  embedded AIVAN runtime; it was never part of this Alembic chain and was
  deleted with the embed.
- No migration was rewritten; Stage 1 added no new revisions.

## Cross-repo hazard (documented, not fixed here)

Revision id `b2c3d4e5f6a7` exists in BOTH repos with different content
(abcdYi: role-switching column reconcile; Giraffe-JP: giraffe_jp service
core). The two applications must never share one `alembic_version` table,
and future revisions in either repo must use freshly generated ids.
Status: REVIEW_REQUIRED (Stage 2, cross-repo item).
