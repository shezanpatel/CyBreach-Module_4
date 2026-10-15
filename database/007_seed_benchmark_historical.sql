INSERT INTO benchmark_historical
(
    tenant_id,
    industry,
    region,
    size_band,
    p25,
    median,
    p75,
    snapshot_date
)
VALUES

-- TENANT-001: 30 days ago
(
    'TENANT-001',
    'Technology',
    'West',
    'Large',
    60.20,
    71.40,
    82.10,
    CURRENT_DATE - INTERVAL '30 days'
),

-- TENANT-001: 60 days ago
(
    'TENANT-001',
    'Technology',
    'West',
    'Large',
    58.30,
    69.50,
    80.70,
    CURRENT_DATE - INTERVAL '60 days'
),

-- TENANT-001: 90 days ago
(
    'TENANT-001',
    'Technology',
    'West',
    'Large',
    55.80,
    67.20,
    78.90,
    CURRENT_DATE - INTERVAL '90 days'
),

-- TENANT-002: 30 days ago
(
    'TENANT-002',
    'Finance',
    'West',
    'Large',
    62.10,
    73.20,
    84.50,
    CURRENT_DATE - INTERVAL '30 days'
),

-- TENANT-002: 60 days ago
(
    'TENANT-002',
    'Finance',
    'West',
    'Large',
    60.40,
    71.10,
    82.70,
    CURRENT_DATE - INTERVAL '60 days'
),

-- TENANT-002: 90 days ago
(
    'TENANT-002',
    'Finance',
    'West',
    'Large',
    57.90,
    68.80,
    80.30,
    CURRENT_DATE - INTERVAL '90 days'
);
