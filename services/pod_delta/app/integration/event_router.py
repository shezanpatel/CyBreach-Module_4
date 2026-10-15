"""Route validated events to thin integration handlers."""

from __future__ import annotations

from app.integration.event_schemas import ValidatedEvent
from app.integration.handlers import IntegrationHandlers


class EventRouter:
    def __init__(self, handlers: IntegrationHandlers) -> None:
        self.handlers = handlers

    async def route(self, event: ValidatedEvent) -> None:
        if event.event_type == "mod3.score":
            await self.handlers.handle_score(event)
            return
        if event.event_type in {
            "wallet.transaction",
            "engagement.lifecycle",
            "engagement.completed",
        }:
            await self.handlers.handle_analytics(event)
        if event.event_type in {
            "achievement.awarded",
            "engagement.lifecycle",
            "engagement.completed",
            "wallet.transaction",
        }:
            await self.handlers.handle_notification(event)
            return
        if event.event_type in {"leaderboard.updated", "benchmark.computed"}:
            await self.handlers.websocket_manager.broadcast(
                event.tenant_id,
                {
                    "type": event.event_type,
                    "tenant_id": event.tenant_id,
                    "data": event.data.model_dump(mode="json"),
                },
            )

