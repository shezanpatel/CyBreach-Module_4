"""Multi-instance WebSocket fan-out via Redis pub/sub."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
from uuid import uuid4

from fastapi import WebSocket
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.core.logging import get_logger
from app.core.settings import settings
from app.services.integration.metrics import WS_CONNECTIONS

logger = get_logger("pod_delta.websocket")

WS_SESSION_KEY = "ws_session:{tenant_id}"
WS_CHANNEL = "{prefix}:{tenant_id}"


class ConnectionManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._local: dict[str, dict[str, WebSocket]] = {}
        self._pubsub: Optional[PubSub] = None
        self._listener_task: Optional[asyncio.Task[None]] = None
        self.instance_id = str(uuid4())

    def channel(self, tenant_id: str) -> str:
        return WS_CHANNEL.format(
            prefix=settings.REDIS_WS_CHANNEL_PREFIX,
            tenant_id=tenant_id,
        )

    def session_key(self, tenant_id: str) -> str:
        return WS_SESSION_KEY.format(tenant_id=tenant_id)

    async def start(self) -> None:
        self._pubsub = self.redis.pubsub()
        pattern = f"{settings.REDIS_WS_CHANNEL_PREFIX}:*"
        await self._pubsub.psubscribe(pattern)
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("websocket_manager_started", instance_id=self.instance_id)

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.aclose()
            self._pubsub = None
        for tenant_id, sockets in list(self._local.items()):
            for ws in list(sockets.values()):
                try:
                    await ws.close()
                except Exception:  # noqa: BLE001
                    pass
            await self._clear_session(tenant_id)
        self._local.clear()
        WS_CONNECTIONS.set(0)

    async def connect(self, tenant_id: str, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid4())
        self._local.setdefault(tenant_id, {})[connection_id] = websocket
        WS_CONNECTIONS.inc()
        await self._touch_session(tenant_id, connection_id)
        logger.info(
            "ws_connected",
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        return connection_id

    async def disconnect(self, tenant_id: str, connection_id: str) -> None:
        sockets = self._local.get(tenant_id, {})
        sockets.pop(connection_id, None)
        if not sockets:
            self._local.pop(tenant_id, None)
            await self.redis.delete(self.session_key(tenant_id))
        else:
            await self._touch_session(tenant_id, connection_id, remove=True)
        WS_CONNECTIONS.dec()
        logger.info(
            "ws_disconnected",
            tenant_id=tenant_id,
            connection_id=connection_id,
        )

    async def _touch_session(
        self,
        tenant_id: str,
        connection_id: str,
        *,
        remove: bool = False,
    ) -> None:
        key = self.session_key(tenant_id)
        field = f"{self.instance_id}:{connection_id}"
        if remove:
            await self.redis.hdel(key, field)
        else:
            await self.redis.hset(key, field, "1")
        await self.redis.expire(key, settings.WS_SESSION_TTL_SECONDS)

    async def _clear_session(self, tenant_id: str) -> None:
        await self.redis.delete(self.session_key(tenant_id))

    async def heartbeat(self, tenant_id: str, connection_id: str) -> None:
        await self._touch_session(tenant_id, connection_id)

    async def broadcast(self, tenant_id: str, message: dict[str, Any]) -> int:
        """Publish for all instances; local listeners deliver to sockets."""
        payload = json.dumps(
            {
                "origin": self.instance_id,
                "tenant_id": tenant_id,
                "message": message,
            }
        )
        receivers = await self.redis.publish(self.channel(tenant_id), payload)
        return int(receivers or 0)

    async def _listen(self) -> None:
        assert self._pubsub is not None
        try:
            async for item in self._pubsub.listen():
                if item is None:
                    continue
                if item.get("type") not in {"pmessage", "message"}:
                    continue
                data = item.get("data")
                if not data or data == 1:
                    continue
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    envelope = json.loads(data)
                except json.JSONDecodeError:
                    continue
                tenant_id = envelope.get("tenant_id")
                message = envelope.get("message")
                if tenant_id and message:
                    await self._deliver_local(tenant_id, message)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("ws_pubsub_listener_failed")

    async def _deliver_local(self, tenant_id: str, message: dict[str, Any]) -> None:
        sockets = list(self._local.get(tenant_id, {}).items())
        stale: list[str] = []
        for connection_id, websocket in sockets:
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001
                stale.append(connection_id)
        for connection_id in stale:
            await self.disconnect(tenant_id, connection_id)

    def local_connection_count(self) -> int:
        return sum(len(v) for v in self._local.values())
