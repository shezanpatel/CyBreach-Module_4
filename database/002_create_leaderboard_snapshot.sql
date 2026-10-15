-- PG-18: Leaderboard snapshot table

CREATE TABLE IF NOT EXISTS leaderboard_snapshot (
    snapshot_id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    dimension VARCHAR(50) NOT NULL,
    dimension_value VARCHAR(100) NOT NULL,
    score NUMERIC(20, 4) NOT NULL,
    delta NUMERIC(20, 4) NOT NULL DEFAULT 0,
    rank INTEGER NOT NULL,
    snapshot_date DATE NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_leaderboard_snapshot_tenant_dimension_date
    ON leaderboard_snapshot (
        tenant_id,
        dimension,
        snapshot_date
    );