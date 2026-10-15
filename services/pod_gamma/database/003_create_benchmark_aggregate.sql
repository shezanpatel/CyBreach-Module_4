CREATE TABLE IF NOT EXISTS benchmark_aggregate (
    industry VARCHAR(255) NOT NULL,
    region VARCHAR(255) NOT NULL,
    size_band VARCHAR(100) NOT NULL,
    peer_count INTEGER NOT NULL CHECK (peer_count >= 0),
    peer_25th NUMERIC,
    peer_median NUMERIC,
    peer_75th NUMERIC
);