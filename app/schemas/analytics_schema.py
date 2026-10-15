from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"   # YYYY-MM, e.g. 2026-09


class AnalyticsBase(BaseModel):
    tenant_id: str
    tenant_name: str

    resilience_score: float = Field(
        ...,
        ge=0,
        le=100
    )

    credit_balance: float = 0.0
    credit_used: float = 0.0

    total_users: int = 0
    active_users: int = 0
    total_visits: int = 0

    avg_session_duration: float = 0.0
    response_time_avg: float = 0.0

    uptime_percentage: float = Field(
        100.0,
        ge=0,
        le=100
    )

    error_count: int = 0

    metrics_json: Optional[Dict[str, Any]] = None

    report_month: str


class AnalyticsCreate(AnalyticsBase):
    credit_balance: float = Field(0.0, ge=0)
    credit_used: float = Field(0.0, ge=0)

    total_users: int = Field(0, ge=0)
    active_users: int = Field(0, ge=0)
    total_visits: int = Field(0, ge=0)

    avg_session_duration: float = Field(0.0, ge=0)
    response_time_avg: float = Field(0.0, ge=0)

    error_count: int = Field(0, ge=0)

    report_month: str = Field(..., pattern=MONTH_PATTERN)

    @model_validator(mode="after")
    def check_active_users(self):
        if self.active_users > self.total_users:
            raise ValueError("active_users cannot be greater than total_users")
        return self


class AnalyticsUpdate(BaseModel):
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None

    resilience_score: Optional[float] = Field(
        None,
        ge=0,
        le=100
    )

    credit_balance: Optional[float] = Field(None, ge=0)
    credit_used: Optional[float] = Field(None, ge=0)

    total_users: Optional[int] = Field(None, ge=0)
    active_users: Optional[int] = Field(None, ge=0)
    total_visits: Optional[int] = Field(None, ge=0)

    avg_session_duration: Optional[float] = Field(None, ge=0)
    response_time_avg: Optional[float] = Field(None, ge=0)

    uptime_percentage: Optional[float] = Field(
        None,
        ge=0,
        le=100
    )

    error_count: Optional[int] = Field(None, ge=0)

    metrics_json: Optional[Dict[str, Any]] = None

    report_month: Optional[str] = Field(None, pattern=MONTH_PATTERN)

    @model_validator(mode="after")
    def check_active_users(self):
        if (
            self.active_users is not None
            and self.total_users is not None
            and self.active_users > self.total_users
        ):
            raise ValueError("active_users cannot be greater than total_users")
        return self


class AnalyticsResponse(AnalyticsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class AnalyticsListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    records: list[AnalyticsResponse]


class DashboardResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    resilience_score: float
    total_users: int
    active_users: int
    total_visits: int
    uptime_percentage: float
    error_count: int


class CreditFlowResponse(BaseModel):
    tenant_id: str
    credit_balance: float
    credit_used: float
    total_credits: float
    usage_percentage: float


class EngagementResponse(BaseModel):
    tenant_id: str
    total_users: int
    active_users: int
    total_visits: int
    avg_session_duration: float
    engagement_percentage: float


class ScoreResponse(BaseModel):
    tenant_id: str
    resilience_score: float


class ScoreTrendResponse(BaseModel):
    tenant_id: str
    current_score: float
    previous_score: Optional[float]
    change: Optional[float]
    change_percentage: Optional[float]
    trend_direction: str


class ReportResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    report_month: str
    resilience_score: float
    credit_balance: float
    credit_used: float
    total_users: int
    active_users: int
    total_visits: int
    uptime_percentage: float
    error_count: int