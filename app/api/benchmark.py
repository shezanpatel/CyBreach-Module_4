import math
import random

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.benchmark_repository import (
    get_benchmark_aggregate,
    get_benchmark_history,
    get_global_benchmark,
)

router = APIRouter(
    prefix="/benchmark",
    tags=["benchmark"],
)


# ============================================================
# Configuration
# ============================================================

# PG-27
MIN_PEER_GROUP_SIZE = 10

# PG-26
EPSILON = 1.0
SENSITIVITY = 100.0

# Section 2 / Section 11.7
DEMO_DATA_LABEL = "seeded demo baseline"


# ============================================================
# Request Schemas
# ============================================================

class BenchmarkRequest(BaseModel):
    """
    Client sends only cohort information.

    Raw peer scores must NOT be supplied by the client.
    """

    industry: str = Field(min_length=1)
    region: str = Field(min_length=1)
    size_band: str = Field(min_length=1)


class RegionalComparisonRequest(BaseModel):
    """
    Request used for PG-25 regional vs global comparison.
    """

    industry: str = Field(min_length=1)
    region: str = Field(min_length=1)
    size_band: str = Field(min_length=1)


# ============================================================
# Response Schemas
# ============================================================

class BenchmarkResult(BaseModel):
    """
    Flat BenchmarkResult contract required by Pod Delta.

    Synthetic benchmark data is explicitly labelled as
    'seeded demo baseline'.
    """

    tenant_id: str
    percentile: float
    peer_median: float
    peer_25th: float
    peer_75th: float
    peer_count: int
    trend: list
    label: str = DEMO_DATA_LABEL


class RegionalComparisonResponse(BaseModel):
    industry: str
    region: str
    size_band: str

    regional_peer_count: int
    regional_median: float

    global_peer_count: int
    global_median: float

    median_difference: float


class BenchmarkTrendItem(BaseModel):
    days_ago: int
    peer_25th: float
    peer_median: float
    peer_75th: float


class BenchmarkTrendResponse(BaseModel):
    tenant_id: str
    trend: list[BenchmarkTrendItem]


# ============================================================
# PG-26: Differential Privacy
# ============================================================

def generate_laplace_noise(scale: float) -> float:
    """
    Generate Laplace-distributed noise.
    """

    u = random.uniform(-0.5, 0.5)

    if u == 0:
        u = 1e-12

    return -scale * math.copysign(
        math.log(1 - 2 * abs(u)),
        u,
    )


def apply_laplace_noise(value: float) -> float:
    """
    Apply calibrated Laplace noise to a benchmark value.

    The result is constrained to the valid security-score
    range of 0-100 and rounded to two decimal places.
    """

    scale = SENSITIVITY / EPSILON

    noisy_value = value + generate_laplace_noise(scale)

    noisy_value = max(
        0.0,
        min(100.0, noisy_value),
    )

    return round(noisy_value, 2)


# ============================================================
# POST /benchmark
#
# Flow:
#
# Client
#   |
#   | { industry, region, size_band }
#   v
# benchmark_aggregate
#   |
#   v
# PG-27: peer_count >= 10
#   |
#   v
# PG-26: Laplace noise
#   |
#   v
# Flat BenchmarkResult
# ============================================================

@router.post(
    "",
    response_model=BenchmarkResult,
)
async def create_benchmark(
    request: BenchmarkRequest,
) -> BenchmarkResult:

    # --------------------------------------------------------
    # Step 1: Query benchmark aggregate
    # --------------------------------------------------------

    peer = await get_benchmark_aggregate(
        industry=request.industry,
        region=request.region,
        size_band=request.size_band,
    )

    if peer is None:
        raise HTTPException(
            status_code=404,
            detail="benchmark cohort not found",
        )

    peer_count = int(peer["peer_count"])

    # --------------------------------------------------------
    # Step 2: PG-27
    # Minimum Peer Group Enforcement
    # --------------------------------------------------------

    if peer_count < MIN_PEER_GROUP_SIZE:
        raise HTTPException(
            status_code=422,
            detail="insufficient peers",
        )

    # --------------------------------------------------------
    # Validate benchmark metrics
    # --------------------------------------------------------

    if (
        peer["peer_25th"] is None
        or peer["peer_median"] is None
        or peer["peer_75th"] is None
    ):
        raise HTTPException(
            status_code=500,
            detail="benchmark metrics unavailable",
        )

    # --------------------------------------------------------
    # Step 3: PG-26
    # Apply Laplace noise to P25, Median and P75
    # --------------------------------------------------------

    noisy_25th = apply_laplace_noise(
        float(peer["peer_25th"])
    )

    noisy_median = apply_laplace_noise(
        float(peer["peer_median"])
    )

    noisy_75th = apply_laplace_noise(
        float(peer["peer_75th"])
    )

    # --------------------------------------------------------
    # Step 4: Build flat BenchmarkResult
    #
    # The current seeded demo repository contains aggregate
    # cohort data rather than individual tenant scores.
    #
    # Therefore:
    # - tenant_id identifies the seeded demo cohort
    # - percentile uses the cohort median as the demo
    #   percentile position
    # - trend starts empty because historical trend is exposed
    #   separately through /benchmark/trend/{tenant_id}
    # --------------------------------------------------------

    demo_tenant_id = (
        f"{peer['industry']}-"
        f"{peer['region']}-"
        f"{peer['size_band']}"
    )

    demo_percentile = round(
        float(peer["peer_median"]),
        2,
    )

    return BenchmarkResult(
        tenant_id=demo_tenant_id,
        percentile=demo_percentile,
        peer_median=noisy_median,
        peer_25th=noisy_25th,
        peer_75th=noisy_75th,
        peer_count=peer_count,
        trend=[],
        label=DEMO_DATA_LABEL,
    )


# ============================================================
# PG-25: Cross-Regional Comparison
#
# Flow:
#
# Client
#   |
#   v
# Regional cohort
#   |
#   +----> Regional median
#   |
#   +----> Global median
#   |
#   v
# Difference = Regional median - Global median
# ============================================================

@router.post(
    "/compare",
    response_model=RegionalComparisonResponse,
    responses={
        403: {
            "description": "Cohort has fewer than 10 peers",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "insufficient peers"
                    }
                }
            },
        }
    },
)
async def compare_regional_benchmark(
    request: RegionalComparisonRequest,
) -> RegionalComparisonResponse:

    # --------------------------------------------------------
    # Step 1: Get regional cohort
    # --------------------------------------------------------

    regional = await get_benchmark_aggregate(
        industry=request.industry,
        region=request.region,
        size_band=request.size_band,
    )

    if regional is None:
        raise HTTPException(
            status_code=404,
            detail="regional benchmark cohort not found",
        )

    regional_peer_count = int(
        regional["peer_count"]
    )

    # --------------------------------------------------------
    # Step 2: PG-27
    # Regional cohort must have at least 10 peers
    # --------------------------------------------------------

    if regional_peer_count < MIN_PEER_GROUP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient peers",
        )

    if regional["peer_median"] is None:
        raise HTTPException(
            status_code=500,
            detail="regional median unavailable",
        )

    # --------------------------------------------------------
    # Step 3: Get global benchmark
    # --------------------------------------------------------

    global_benchmark = await get_global_benchmark()

    if global_benchmark is None:
        raise HTTPException(
            status_code=404,
            detail="global benchmark not found",
        )

    global_peer_count = int(
        global_benchmark["peer_count"]
    )

    # --------------------------------------------------------
    # Step 4: PG-27 for global cohort
    # --------------------------------------------------------

    if global_peer_count < MIN_PEER_GROUP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient peers",
        )

    if global_benchmark["peer_median"] is None:
        raise HTTPException(
            status_code=500,
            detail="global median unavailable",
        )

    # --------------------------------------------------------
    # Step 5: Calculate regional vs global difference
    # --------------------------------------------------------

    regional_median = float(
        regional["peer_median"]
    )

    global_median = float(
        global_benchmark["peer_median"]
    )

    median_difference = round(
        regional_median - global_median,
        2,
    )

    # --------------------------------------------------------
    # Step 6: Return comparison
    # --------------------------------------------------------

    return RegionalComparisonResponse(
        industry=regional["industry"],
        region=regional["region"],
        size_band=regional["size_band"],
        regional_peer_count=regional_peer_count,
        regional_median=regional_median,
        global_peer_count=global_peer_count,
        global_median=global_median,
        median_difference=median_difference,
    )


# ============================================================
# PG-28: Historical Percentile Trend
#
# GET /benchmark/trend/{tenant_id}
#
# Returns historical P25 / Median / P75 progression.
# ============================================================

@router.get(
    "/trend/{tenant_id}",
    response_model=BenchmarkTrendResponse,
)
async def get_benchmark_trend(
    tenant_id: str,
) -> BenchmarkTrendResponse:

    # --------------------------------------------------------
    # Validate tenant ID
    # --------------------------------------------------------

    if not tenant_id.strip():
        raise HTTPException(
            status_code=422,
            detail="tenant_id cannot be empty",
        )

    # --------------------------------------------------------
    # Step 1: Query historical benchmark records
    # --------------------------------------------------------

    history = await get_benchmark_history(
        tenant_id
    )

    if not history:
        raise HTTPException(
            status_code=404,
            detail="benchmark history not found",
        )

    # --------------------------------------------------------
    # Step 2: Select 30 / 60 / 90-day records
    # --------------------------------------------------------

    allowed_days = {30, 60, 90}

    trend = []

    for record in history:

        if record["days_ago"] not in allowed_days:
            continue

        trend.append(
            BenchmarkTrendItem(
                days_ago=int(record["days_ago"]),
                peer_25th=round(
                    float(record["p25"]),
                    2,
                ),
                peer_median=round(
                    float(record["median"]),
                    2,
                ),
                peer_75th=round(
                    float(record["p75"]),
                    2,
                ),
            )
        )

    # --------------------------------------------------------
    # Step 3: Make sure required timeline exists
    # --------------------------------------------------------

    available_days = {
        item.days_ago
        for item in trend
    }

    missing_days = allowed_days - available_days

    if missing_days:
        raise HTTPException(
            status_code=404,
            detail=(
                "historical benchmark data missing for: "
                + ", ".join(
                    str(day)
                    for day in sorted(missing_days)
                )
                + " days"
            ),
        )

    # --------------------------------------------------------
    # Step 4: Sort newest -> oldest
    # --------------------------------------------------------

    trend.sort(
        key=lambda item: item.days_ago
    )

    # --------------------------------------------------------
    # Step 5: Return historical progression
    # --------------------------------------------------------

    return BenchmarkTrendResponse(
        tenant_id=tenant_id,
        trend=trend,
    )