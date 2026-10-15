-- PG-19: Sanitize/anonymize historical leaderboard snapshots
--
-- Purpose:
--   Remove the original tenant identifier from historical snapshots while
--   preserving score, delta, rank, dimension, dimension_value, and date so
--   historical/improvement calculations can continue to work.
--
-- PostgreSQL
--
-- Usage:
--   Replace :tenant_id with the tenant being opted out.
--   Example:
--   WHERE tenant_id = 'CORP-001'
--
-- The deterministic hash keeps snapshots for the same tenant linked without
-- exposing the original tenant_id. It also avoids collisions with the
-- existing UNIQUE (tenant_id, dimension, snapshot_date) index.

BEGIN;

UPDATE leaderboard_snapshot
SET tenant_id = 'ANON-' || substr(md5(tenant_id), 1, 16)
WHERE tenant_id = :tenant_id;

COMMIT;
