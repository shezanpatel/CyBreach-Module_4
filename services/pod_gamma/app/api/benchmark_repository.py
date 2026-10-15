BENCHMARK_DATA = [
    {
        "industry": "Technology",
        "region": "West",
        "size_band": "Large",
        "peer_count": 20,
        "peer_25th": 65.20,
        "peer_median": 76.40,
        "peer_75th": 88.10,
    },
    {
        "industry": "Technology",
        "region": "West",
        "size_band": "Medium",
        "peer_count": 18,
        "peer_25th": 61.30,
        "peer_median": 72.50,
        "peer_75th": 84.70,
    },
    {
        "industry": "Technology",
        "region": "North",
        "size_band": "Large",
        "peer_count": 16,
        "peer_25th": 62.50,
        "peer_median": 75.10,
        "peer_75th": 87.30,
    },
    {
        "industry": "Finance",
        "region": "West",
        "size_band": "Large",
        "peer_count": 15,
        "peer_25th": 60.10,
        "peer_median": 71.20,
        "peer_75th": 83.50,
    },
    {
        "industry": "Finance",
        "region": "North",
        "size_band": "Medium",
        "peer_count": 19,
        "peer_25th": 64.20,
        "peer_median": 73.60,
        "peer_75th": 85.40,
    },
    {
        "industry": "Healthcare",
        "region": "West",
        "size_band": "Large",
        "peer_count": 17,
        "peer_25th": 63.40,
        "peer_median": 74.80,
        "peer_75th": 86.20,
    },
    {
        "industry": "Healthcare",
        "region": "South",
        "size_band": "Medium",
        "peer_count": 15,
        "peer_25th": 58.70,
        "peer_median": 69.90,
        "peer_75th": 81.50,
    },

    # PG-27 test case: fewer than 10 peers
    {
        "industry": "Finance",
        "region": "West",
        "size_band": "Small",
        "peer_count": 8,
        "peer_25th": 55.00,
        "peer_median": 63.00,
        "peer_75th": 72.00,
    },

    # PG-25 global benchmark
    {
        "industry": "ALL",
        "region": "GLOBAL",
        "size_band": "ALL",
        "peer_count": 100,
        "peer_25th": 60.00,
        "peer_median": 72.00,
        "peer_75th": 84.00,
    },
]


async def get_benchmark_aggregate(
    industry: str,
    region: str,
    size_band: str,
):
    """
    Return the benchmark aggregate for a specific cohort.
    """

    for record in BENCHMARK_DATA:
        if (
            record["industry"] == industry
            and record["region"] == region
            and record["size_band"] == size_band
        ):
            return record

    return None


async def get_global_benchmark():
    """
    Return the global benchmark aggregate used by PG-25.
    """

    for record in BENCHMARK_DATA:
        if (
            record["industry"] == "ALL"
            and record["region"] == "GLOBAL"
            and record["size_band"] == "ALL"
        ):
            return record

    return None


# ============================================================
# PG-28 Historical Benchmark Test Data
# ============================================================

BENCHMARK_HISTORY = [
    # TENANT-001: 30 days ago
    {
        "tenant_id": "TENANT-001",
        "industry": "Technology",
        "region": "West",
        "size_band": "Large",
        "p25": 60.20,
        "median": 71.40,
        "p75": 82.10,
        "days_ago": 30,
    },

    # TENANT-001: 60 days ago
    {
        "tenant_id": "TENANT-001",
        "industry": "Technology",
        "region": "West",
        "size_band": "Large",
        "p25": 58.30,
        "median": 69.50,
        "p75": 80.70,
        "days_ago": 60,
    },

    # TENANT-001: 90 days ago
    {
        "tenant_id": "TENANT-001",
        "industry": "Technology",
        "region": "West",
        "size_band": "Large",
        "p25": 55.80,
        "median": 67.20,
        "p75": 78.90,
        "days_ago": 90,
    },

    # TENANT-002: 30 days ago
    {
        "tenant_id": "TENANT-002",
        "industry": "Finance",
        "region": "West",
        "size_band": "Large",
        "p25": 62.10,
        "median": 73.20,
        "p75": 84.50,
        "days_ago": 30,
    },

    # TENANT-002: 60 days ago
    {
        "tenant_id": "TENANT-002",
        "industry": "Finance",
        "region": "West",
        "size_band": "Large",
        "p25": 60.40,
        "median": 71.10,
        "p75": 82.70,
        "days_ago": 60,
    },

    # TENANT-002: 90 days ago
    {
        "tenant_id": "TENANT-002",
        "industry": "Finance",
        "region": "West",
        "size_band": "Large",
        "p25": 57.90,
        "median": 68.80,
        "p75": 80.30,
        "days_ago": 90,
    },
]


async def get_benchmark_history(tenant_id: str):
    """
    Return historical benchmark snapshots for a tenant.

    This is currently local test data.
    The production implementation will query
    benchmark_historical from the database.
    """

    return [
        record
        for record in BENCHMARK_HISTORY
        if record["tenant_id"] == tenant_id
    ]