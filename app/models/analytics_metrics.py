from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    JSON,
    Index
)

from app.database.db_connection import Base


class AnalyticsMetric(Base):
    __tablename__ = "analytics_metrics"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(
        String,
        nullable=False,
        index=True
    )

    tenant_name = Column(
        String,
        nullable=False
    )

    resilience_score = Column(
        Float,
        nullable=False
    )

    credit_balance = Column(
        Float,
        nullable=False,
        default=0.0
    )

    credit_used = Column(
        Float,
        nullable=False,
        default=0.0
    )

    total_users = Column(
        Integer,
        nullable=False,
        default=0
    )

    active_users = Column(
        Integer,
        nullable=False,
        default=0
    )

    total_visits = Column(
        Integer,
        nullable=False,
        default=0
    )

    avg_session_duration = Column(
        Float,
        nullable=False,
        default=0.0
    )

    response_time_avg = Column(
        Float,
        nullable=False,
        default=0.0
    )

    uptime_percentage = Column(
        Float,
        nullable=False,
        default=100.0
    )

    error_count = Column(
        Integer,
        nullable=False,
        default=0
    )

    metrics_json = Column(
        JSON,
        nullable=True
    )

    report_month = Column(
        String,
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


Index(
    "ix_analytics_tenant_month",
    AnalyticsMetric.tenant_id,
    AnalyticsMetric.report_month
)