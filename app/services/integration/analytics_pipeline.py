"""Hand off consumed events to the existing Analytics Engine (not ClickHouse queries)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.settings import settings
from app.core.exceptions import AnalyticsNotFoundException
from app.database.db_connection import SessionLocal
from app.events.base import EventEnvelope
from app.events.published import AnalyticsReportEvent
from app.schemas.analytics_schema import AnalyticsCreate, AnalyticsUpdate
from app.services.analytics_engine_service import (
    create_analytics,
    get_analytics_by_tenant,
    update_analytics,
)
from app.services.integration.kafka.producer import KafkaProducerService

logger = get_logger("pod_delta.analytics_pipeline")

BUFFER_KEY = "analytics:buffer:{tenant_id}"


class AnalyticsPipeline:
    def __init__(self, producer: KafkaProducerService) -> None:
        self.producer = producer

    async def ingest(self, event: EventEnvelope) -> None:
        redis = await get_redis()
        key = BUFFER_KEY.format(tenant_id=event.tenant_id)
        await redis.rpush(
            key,
            json.dumps(
                {
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "occurred_at": event.occurred_at.isoformat(),
                    "correlation_id": event.correlation_id,
                }
            ),
        )
        await redis.expire(key, settings.ANALYTICS_FLUSH_INTERVAL_SECONDS * 2)

    async def flush_tenant(
        self,
        tenant_id: str,
        *,
        report_kind: str = "scheduled",
        extra: Optional[dict[str, Any]] = None,
    ) -> Optional[AnalyticsReportEvent]:
        redis = await get_redis()
        key = BUFFER_KEY.format(tenant_id=tenant_id)
        events = await redis.lrange(key, 0, -1)
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        db = SessionLocal()
        try:
            payload = extra or {}
            score = float(payload.get("resilience_score", 0.0) or 0.0)
            try:
                existing = get_analytics_by_tenant(db, tenant_id)
                updated = update_analytics(
                    db,
                    existing.id,
                    AnalyticsUpdate(
                        resilience_score=score or existing.resilience_score,
                        metrics_json={
                            "ingested_events": len(events),
                            "source": "pod-delta-integration",
                            **payload,
                        },
                        report_month=month,
                    ),
                )
                record_id = updated.id
                summary = {
                    "resilience_score": updated.resilience_score,
                    "ingested_events": len(events),
                }
            except AnalyticsNotFoundException:
                created = create_analytics(
                    db,
                    AnalyticsCreate(
                        tenant_id=tenant_id,
                        tenant_name=payload.get("tenant_name", tenant_id),
                        resilience_score=score,
                        report_month=month,
                        metrics_json={
                            "ingested_events": len(events),
                            "source": "pod-delta-integration",
                            **payload,
                        },
                    ),
                )
                record_id = created.id
                summary = {
                    "resilience_score": created.resilience_score,
                    "ingested_events": len(events),
                }

            report = AnalyticsReportEvent(
                tenant_id=tenant_id,
                report_month=month,
                report_kind=report_kind,  # type: ignore[arg-type]
                record_id=record_id,
                summary=summary,
            )
            await self.producer.publish_owned(report)
            await redis.delete(key)
            logger.info(
                "analytics_report_emitted",
                tenant_id=tenant_id,
                event_type="analytics.report",
                correlation_id=report.correlation_id,
                record_id=record_id,
            )
            return report
        except Exception:
            logger.exception("analytics_flush_failed", tenant_id=tenant_id)
            db.rollback()
            return None
        finally:
            db.close()

    async def flush_all(self, *, report_kind: str = "scheduled") -> int:
        redis = await get_redis()
        flushed = 0
        async for key in redis.scan_iter(match="analytics:buffer:*"):
            tenant_id = str(key).split("analytics:buffer:", 1)[-1]
            result = await self.flush_tenant(tenant_id, report_kind=report_kind)
            if result is not None:
                flushed += 1
        return flushed
