-- GPM Database Permission Grants
-- Run as a PostgreSQL superuser / schema owner after migrations complete.
--
-- abcdyi_service = the PostgreSQL role used by the abcdyi application.
-- Adjust the role name to match your deployment.
--
-- Design: abcdyi has INSERT-only on the buffer table and SELECT-only on
-- all other GPM tables. It cannot write benchmark data or verified records.
-- This is enforced at the database layer, not just application code.

-- 1. Grant USAGE on the gpm schema so abcdyi can see the objects.
GRANT USAGE ON SCHEMA gpm TO abcdyi_service;

-- 2. READ-ONLY access to reference and benchmark tables.
GRANT SELECT ON gpm.fabric_db              TO abcdyi_service;
GRANT SELECT ON gpm.sku_process_attribute  TO abcdyi_service;
GRANT SELECT ON gpm.process_benchmark      TO abcdyi_service;
GRANT SELECT ON gpm.giraffe_universal_model TO abcdyi_service;

-- 3. READ-ONLY access to verified data (abcdyi may read it for analytics/audit,
--    but cannot write to it — only GPM's internal promotion service can).
GRANT SELECT ON gpm.verified_business_data TO abcdyi_service;

-- 4. The ONLY table abcdyi can write to is the buffer table.
--    INSERT only — no UPDATE, no DELETE, no TRUNCATE.
GRANT SELECT, INSERT ON gpm.incoming_order_data TO abcdyi_service;

-- 5. gpm_service = the PostgreSQL role used by the GPM application itself.
--    It owns all objects in the gpm schema and has full access.
GRANT ALL PRIVILEGES ON SCHEMA gpm TO gpm_service;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gpm TO gpm_service;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gpm TO gpm_service;

-- 6. Client-proprietary isolation for universal model training (§5.4).
--    gpm_training_role = the role used by automated model-training pipelines.
--    It may ONLY read through the filtered view, never the base verified_business_data.
--    client_proprietary rows are therefore structurally excluded from training data.
GRANT USAGE ON SCHEMA gpm TO gpm_training_role;
GRANT SELECT ON gpm.v_training_data_universal TO gpm_training_role;
REVOKE ALL ON gpm.verified_business_data FROM gpm_training_role;

-- To verify abcdyi_service cannot write to protected tables, test:
--   SET ROLE abcdyi_service;
--   INSERT INTO gpm.process_benchmark (...) VALUES (...);
--   -- Expected: ERROR: permission denied for table process_benchmark
--   INSERT INTO gpm.incoming_order_data (...) VALUES (...);
--   -- Expected: INSERT 0 1  (success)
