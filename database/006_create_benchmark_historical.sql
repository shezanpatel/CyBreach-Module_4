CREATE TABLE IF NOT EXISTS benchmark_historical (
    tenant_id VARCHAR(255) NOT NULL,
    industry VARCHAR(255) NOT NULL,
    region VARCHAR(255) NOT NULL,
    size_band VARCHAR(100) NOT NULL,
    p25 NUMERIC,
    median NUMERIC,
    p75 NUMERIC,
    snapshot_date DATE NOT NULL,

    CONSTRAINT uq_benchmark_historical_tenant_snapshot
    	UNIQUE (tenant_id, snapshot_date)
);
