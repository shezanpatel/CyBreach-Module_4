from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.analytics_metrics import AnalyticsMetric
from app.schemas.analytics_schema import (
    AnalyticsCreate,
    AnalyticsUpdate
)
from app.core.exceptions import (
    AnalyticsNotFoundException,
    AnalyticsDatabaseException
)


def create_analytics(
    db: Session,
    analytics: AnalyticsCreate
):
    try:
        db_record = AnalyticsMetric(
            **analytics.model_dump()
        )

        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        return db_record

    except Exception as exc:
        db.rollback()
        raise AnalyticsDatabaseException(
            f"Failed to create analytics record: {str(exc)}"
        )


def get_all_analytics(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[str] = None,
    report_month: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None
):
    query = db.query(AnalyticsMetric)

    if tenant_id:
        query = query.filter(
            AnalyticsMetric.tenant_id == tenant_id
        )

    if report_month:
        query = query.filter(
            AnalyticsMetric.report_month == report_month
        )

    if start_date:
        query = query.filter(
            AnalyticsMetric.created_at >= start_date
        )

    if end_date:
        query = query.filter(
            AnalyticsMetric.created_at <= end_date
        )

    if min_score is not None:
        query = query.filter(
            AnalyticsMetric.resilience_score >= min_score
        )

    if max_score is not None:
        query = query.filter(
            AnalyticsMetric.resilience_score <= max_score
        )

    total = query.count()

    records = (
        query
        .order_by(AnalyticsMetric.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "records": records
    }


def get_analytics_by_id(
    db: Session,
    record_id: int
):
    record = (
        db.query(AnalyticsMetric)
        .filter(AnalyticsMetric.id == record_id)
        .first()
    )

    if not record:
        raise AnalyticsNotFoundException(
            f"Analytics record with ID {record_id} not found"
        )

    return record


def get_analytics_by_tenant(
    db: Session,
    tenant_id: str
):
    record = (
        db.query(AnalyticsMetric)
        .filter(
            AnalyticsMetric.tenant_id == tenant_id
        )
        .order_by(AnalyticsMetric.id.desc())
        .first()
    )

    if not record:
        raise AnalyticsNotFoundException(
            f"Analytics record for tenant {tenant_id} not found"
        )

    return record


def update_analytics(
    db: Session,
    record_id: int,
    analytics: AnalyticsUpdate
):
    record = get_analytics_by_id(
        db,
        record_id
    )

    update_data = analytics.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(record, key, value)

    record.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(record)

        return record

    except Exception as exc:
        db.rollback()

        raise AnalyticsDatabaseException(
            f"Failed to update analytics record: {str(exc)}"
        )


def delete_analytics(
    db: Session,
    record_id: int
):
    record = get_analytics_by_id(
        db,
        record_id
    )

    try:
        db.delete(record)
        db.commit()

        return {
            "message": (
                f"Analytics record with ID "
                f"{record_id} deleted successfully"
            )
        }

    except Exception as exc:
        db.rollback()

        raise AnalyticsDatabaseException(
            f"Failed to delete analytics record: {str(exc)}"
        )


def get_dashboard(
    db: Session,
    tenant_id: str
):
    record = get_analytics_by_tenant(
        db,
        tenant_id
    )

    return {
        "tenant_id": record.tenant_id,
        "tenant_name": record.tenant_name,
        "resilience_score": record.resilience_score,
        "total_users": record.total_users,
        "active_users": record.active_users,
        "total_visits": record.total_visits,
        "uptime_percentage": record.uptime_percentage,
        "error_count": record.error_count
    }


def get_credit_flow(
    db: Session,
    tenant_id: str
):
    record = get_analytics_by_tenant(
        db,
        tenant_id
    )

    total_credits = (
        record.credit_balance +
        record.credit_used
    )

    if total_credits > 0:
        usage_percentage = (
            record.credit_used /
            total_credits
        ) * 100
    else:
        usage_percentage = 0.0

    return {
        "tenant_id": tenant_id,
        "credit_balance": record.credit_balance,
        "credit_used": record.credit_used,
        "total_credits": total_credits,
        "usage_percentage": round(
            usage_percentage,
            2
        )
    }


def get_engagement(
    db: Session,
    tenant_id: str
):
    record = get_analytics_by_tenant(
        db,
        tenant_id
    )

    if record.total_users > 0:
        engagement_percentage = (
            record.active_users /
            record.total_users
        ) * 100
    else:
        engagement_percentage = 0.0

    return {
        "tenant_id": tenant_id,
        "total_users": record.total_users,
        "active_users": record.active_users,
        "total_visits": record.total_visits,
        "avg_session_duration":
            record.avg_session_duration,
        "engagement_percentage":
            round(
                engagement_percentage,
                2
            )
    }


def get_score(
    db: Session,
    tenant_id: str
):
    record = get_analytics_by_tenant(
        db,
        tenant_id
    )

    return {
        "tenant_id": tenant_id,
        "resilience_score":
            record.resilience_score
    }


def get_score_trend(
    db: Session,
    tenant_id: str
):
    records = (
        db.query(AnalyticsMetric)
        .filter(
            AnalyticsMetric.tenant_id == tenant_id
        )
        .order_by(
            AnalyticsMetric.report_month.desc()
        )
        .limit(2)
        .all()
    )

    if not records:
        raise AnalyticsNotFoundException(
            f"No analytics data found for tenant {tenant_id}"
        )

    current = records[0]

    if len(records) == 1:
        return {
            "tenant_id": tenant_id,
            "current_score":
                current.resilience_score,
            "previous_score": None,
            "change": None,
            "change_percentage": None,
            "trend_direction": "Stable"
        }

    previous = records[1]

    change = (
        current.resilience_score -
        previous.resilience_score
    )

    if previous.resilience_score != 0:
        change_percentage = (
            change /
            previous.resilience_score
        ) * 100
    else:
        change_percentage = 0.0

    if change > 0:
        direction = "Increasing"
    elif change < 0:
        direction = "Decreasing"
    else:
        direction = "Stable"

    return {
        "tenant_id": tenant_id,
        "current_score":
            current.resilience_score,
        "previous_score":
            previous.resilience_score,
        "change": round(change, 2),
        "change_percentage":
            round(change_percentage, 2),
        "trend_direction": direction
    }


def get_report(
    db: Session,
    tenant_id: str
):
    record = get_analytics_by_tenant(
        db,
        tenant_id
    )

    return {
        "tenant_id": record.tenant_id,
        "tenant_name": record.tenant_name,
        "report_month": record.report_month,
        "resilience_score":
            record.resilience_score,
        "credit_balance":
            record.credit_balance,
        "credit_used":
            record.credit_used,
        "total_users":
            record.total_users,
        "active_users":
            record.active_users,
        "total_visits":
            record.total_visits,
        "uptime_percentage":
            record.uptime_percentage,
        "error_count":
            record.error_count
    }