"""Tenant-scoped WebSocket manager with Redis pub/sub for multi-instance fan-out."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi import WebSocket
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.core.settings import settings

WS_SESSION_KEY = "ws_session:{tenant_id}"


class WebSocketManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.instance_id = str(uuid4())
        self._connections: dict[str, dict[str, WebSocket]] = {}
        self._pubsub: PubSub | None = None
        self._listener: asyncio.Task[None] | None = None

    def channel(self, tenant_id: str) -> str:
        return f"{settings.REDIS_WS_CHANNEL_PREFIX}:{tenant_id}"

    def session_key(self, tenant_id: str) -> str:
        return WS_SESSION_KEY.format(tenant_id=tenant_id)

    async def start(self) -> None:
        self._pubsub = self.redis.pubsub()
        await self._pubsub.psubscribe(f"{settings.REDIS_WS_CHANNEL_PREFIX}:*")
        self._listener = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            try:
                await self._listener
            except asyncio.CancelledError:
                pass
        if self._pubsub is not None:
            await self._pubsub.aclose()
            self._pubsub = None
        for tenant_id, sockets in list(self._connections.items()):
            for websocket in list(sockets.values()):
                await websocket.close()
            await self.redis.delete(self.session_key(tenant_id))
        self._connections.clear()

    async def connect(self, tenant_id: str, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid4())
        self._connections.setdefault(tenant_id, {})[connection_id] = websocket
        await self.heartbeat(tenant_id, connection_id)
        return connection_id

    async def disconnect(self, tenant_id: str, connection_id: str) -> None:
        sockets = self._connections.get(tenant_id, {})
        sockets.pop(connection_id, None)
        await self.redis.hdel(self.session_key(tenant_id), f"{self.instance_id}:{connection_id}")
        if not sockets:
            self._connections.pop(tenant_id, None)
            await self.redis.delete(self.session_key(tenant_id))

    async def heartbeat(self, tenant_id: str, connection_id: str) -> None:
        key = self.session_key(tenant_id)
        await self.redis.hset(key, f"{self.instance_id}:{connection_id}", "1")
        await self.redis.expire(key, settings.WS_SESSION_TTL_SECONDS)

    async def broadcast(self, tenant_id: str, message: dict[str, Any]) -> int:
        payload = json.dumps({"tenant_id": tenant_id, "message": message})
        receivers = await self.redis.publish(self.channel(tenant_id), payload)
        return int(receivers or 0)

    async def _listen(self) -> None:
        assert self._pubsub is not None
        async for item in self._pubsub.listen():
            if item.get("type") not in {"pmessage", "message"}:
                continue
            raw = item.get("data")
            if not raw or raw == 1:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            payload = json.loads(raw)
            await self._deliver_local(payload["tenant_id"], payload["message"])

    async def _deliver_local(self, tenant_id: str, message: dict[str, Any]) -> None:
        stale: list[str] = []
        for connection_id, websocket in list(self._connections.get(tenant_id, {}).items()):
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(connection_id)
        for connection_id in stale:
            await self.disconnect(tenant_id, connection_id)

    def local_connection_count(self) -> int:
        return sum(len(sockets) for sockets in self._connections.values())

