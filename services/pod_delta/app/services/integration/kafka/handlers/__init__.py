"""Kafka event handlers."""

from __future__ import annotations

from app.core.logging import get_logger
from app.events.consumed import (
    AchievementAwardedEvent,
    BenchmarkComputedEvent,
    EngagementCompletedEvent,
    EngagementLifecycleEvent,
    LeaderboardUpdatedEvent,
    Mod3ScoreEvent,
    WalletTransactionEvent,
)
from app.schemas.notification_schema import NotificationPriority
from app.services.integration.analytics_pipeline import AnalyticsPipeline
from app.services.integration.kafka.producer import KafkaProducerService
from app.services.integration.orchestrator import NotificationOrchestrator
from app.services.integration.score_flow import ScoreDisplayFlow
from app.services.integration.websocket.manager import ConnectionManager

logger = get_logger("pod_delta.handlers")


class EventHandlers:
    def __init__(
        self,
        producer: KafkaProducerService,
        ws_manager: ConnectionManager,
    ) -> None:
        self.orchestrator = NotificationOrchestrator(producer, ws_manager)
        self.score_flow = ScoreDisplayFlow(producer, ws_manager)
        self.analytics = AnalyticsPipeline(producer)
        self.ws_manager = ws_manager

    async def wallet_transaction(self, event: WalletTransactionEvent) -> None:
        await self.analytics.ingest(event)
        verb = "credited to" if event.direction == "credit" else "debited from"
        await self.orchestrator.handle_event(
            event,
            title="Wallet activity",
            message=(
                f"{event.amount} {event.currency} {verb} tenant {event.tenant_id}"
            ),
            priority=NotificationPriority.HIGH,
            user_id=event.user_id,
        )

    async def engagement_lifecycle(self, event: EngagementLifecycleEvent) -> None:
        await self.analytics.ingest(event)
        await self.orchestrator.handle_event(
            event,
            title="Engagement update",
            message=f"Engagement {event.engagement_id} moved to {event.stage}",
            user_id=event.user_id,
        )

    async def engagement_completed(self, event: EngagementCompletedEvent) -> None:
        await self.analytics.ingest(event)
        await self.orchestrator.handle_event(
            event,
            title="Engagement completed",
            message=(
                f"Engagement {event.engagement_id} finished with {event.outcome}"
            ),
            priority=NotificationPriority.HIGH,
            user_id=event.user_id,
        )

    async def mod3_score(self, event: Mod3ScoreEvent) -> None:
        await self.analytics.ingest(event)
        await self.score_flow.handle(event)

    async def achievement_awarded(self, event: AchievementAwardedEvent) -> None:
        await self.analytics.ingest(event)
        await self.orchestrator.handle_event(
            event,
            title="Achievement unlocked",
            message=f"{event.achievement_name} awarded (+{event.points})",
            priority=NotificationPriority.HIGH,
            user_id=event.user_id,
        )

    async def leaderboard_updated(self, event: LeaderboardUpdatedEvent) -> None:
        await self.analytics.ingest(event)
        await self.ws_manager.broadcast(
            event.tenant_id,
            {
                "type": "leaderboard_updated",
                "tenant_id": event.tenant_id,
                "board_id": event.board_id,
                "rankings": event.rankings,
            },
        )

    async def benchmark_computed(self, event: BenchmarkComputedEvent) -> None:
        await self.analytics.ingest(event)
        await self.ws_manager.broadcast(
            event.tenant_id,
            {
                "type": "benchmark_computed",
                "tenant_id": event.tenant_id,
                "benchmark_id": event.benchmark_id,
                "percentile": event.percentile,
                "peer_group": event.peer_group,
                "metrics": event.metrics,
            },
        )
