from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status
)

from sqlalchemy.orm import Session

from app.database.db_connection import get_db

from app.schemas.analytics_schema import (
    AnalyticsCreate,
    AnalyticsUpdate,
    AnalyticsResponse,
    AnalyticsListResponse,
    DashboardResponse,
    CreditFlowResponse,
    EngagementResponse,
    ScoreResponse,
    ScoreTrendResponse,
    ReportResponse
)

from app.services.analytics_engine_service import (
    create_analytics,
    get_all_analytics,
    get_analytics_by_id,
    get_analytics_by_tenant,
    update_analytics,
    delete_analytics,
    get_dashboard,
    get_credit_flow,
    get_engagement,
    get_score,
    get_score_trend,
    get_report
)

from app.core.exceptions import (
    AnalyticsValidationException
)


router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)


# --------------------------------------------------
# CREATE
# --------------------------------------------------

@router.post(
    "",
    response_model=AnalyticsResponse,
    status_code=status.HTTP_201_CREATED
)
def create_analytics_record(
    analytics: AnalyticsCreate,
    db: Session = Depends(get_db)
):
    return create_analytics(
        db,
        analytics
    )


# --------------------------------------------------
# GET ALL + PAGINATION + FILTERS
# --------------------------------------------------

@router.get(
    "",
    response_model=AnalyticsListResponse
)
def read_analytics(
    skip: int = Query(
        0,
        ge=0
    ),

    limit: int = Query(
        100,
        ge=1,
        le=1000
    ),

    tenant_id: Optional[str] = None,

    report_month: Optional[str] = None,

    start_date: Optional[datetime] = None,

    end_date: Optional[datetime] = None,

    min_score: Optional[float] = Query(
        None,
        ge=0,
        le=100
    ),

    max_score: Optional[float] = Query(
        None,
        ge=0,
        le=100
    ),

    db: Session = Depends(get_db)
):
    if (
        min_score is not None
        and max_score is not None
        and min_score > max_score
    ):
        raise AnalyticsValidationException(
            "min_score cannot be greater than max_score"
        )

    return get_all_analytics(
        db=db,
        skip=skip,
        limit=limit,
        tenant_id=tenant_id,
        report_month=report_month,
        start_date=start_date,
        end_date=end_date,
        min_score=min_score,
        max_score=max_score
    )


# --------------------------------------------------
# GET BY TENANT
# --------------------------------------------------

@router.get(
    "/tenant/{tenant_id}",
    response_model=AnalyticsResponse
)
def read_by_tenant(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    return get_analytics_by_tenant(
        db,
        tenant_id
    )


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@router.get(
    "/dashboard/{tenant_id}",
    response_model=DashboardResponse
)
def dashboard(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    return get_dashboard(
        db,
        tenant_id
    )


# --------------------------------------------------
# CREDIT FLOW
# --------------------------------------------------

@router.get(
    "/credit-flow/{tenant_id}",
    response_model=CreditFlowResponse
)
def credit_flow(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    return get_credit_flow(
        db,
        tenant_id
    )


# --------------------------------------------------
# ENGAGEMENT
# --------------------------------------------------

@router.get(
    "/engagement/{tenant_id}",
    response_model=EngagementResponse
)
def engagement(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    return get_engagement(
        db,
        tenant_id
    )


# --------------------------------------------------
# SCORE
# --------------------------------------------------

@router.get(
    "/score/{tenant_id}",
    response_model=ScoreResponse
)
def score(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    return get_score(
        db,
        tenant_id
    )


# --------------------------------------------------
# SCORE TREND
# --------------------------------------------------

@router.get(
    "/score-trend/{tenant_id}",
    response_model=ScoreTrendResponse
)
def score_trend(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    return get_score_trend(
        db,
        tenant_id
    )


# --------------------------------------------------
# REPORT
# --------------------------------------------------

@router.get(
    "/report/{tenant_id}",
    response_model=ReportResponse
)
def report(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    return get_report(
        db,
        tenant_id
    )


# --------------------------------------------------
# GET BY ID
# --------------------------------------------------

@router.get(
    "/{record_id}",
    response_model=AnalyticsResponse
)
def read_by_id(
    record_id: int,
    db: Session = Depends(get_db)
):
    return get_analytics_by_id(
        db,
        record_id
    )


# --------------------------------------------------
# UPDATE
# --------------------------------------------------

@router.put(
    "/{record_id}",
    response_model=AnalyticsResponse
)
def update_record(
    record_id: int,
    analytics: AnalyticsUpdate,
    db: Session = Depends(get_db)
):
    return update_analytics(
        db,
        record_id,
        analytics
    )


# --------------------------------------------------
# DELETE
# --------------------------------------------------

@router.delete(
    "/{record_id}"
)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    return delete_analytics(
        db,
        record_id
    )