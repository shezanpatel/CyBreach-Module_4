import asyncio
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis
from starlette.websockets import WebSocketState

from app.core.redis import set_redis_for_tests
from app.services.integration.runtime import set_runtime_for_tests
from app.services.integration.websocket.manager import ConnectionManager


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.accepted = False
        self.client_state = WebSocketState.CONNECTED

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000) -> None:
        self.client_state = WebSocketState.DISCONNECTED


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    set_redis_for_tests(client)
    yield client
    set_redis_for_tests(None)
    await client.aclose()


async def test_websocket_connect_session_and_broadcast(redis):
    manager = ConnectionManager(redis)
    await manager.start()
    set_runtime_for_tests(ws_manager=manager)
    ws = FakeWebSocket()
    connection_id = await manager.connect("tenant-ws", ws)
    assert ws.accepted is True
    session = await redis.hgetall("ws_session:tenant-ws")
    assert session
    await manager.broadcast(
        "tenant-ws",
        {"type": "score_update", "score": 12},
    )
    await asyncio.sleep(0.05)
    assert any(item.get("type") == "score_update" for item in ws.sent)
    await manager.disconnect("tenant-ws", connection_id)
    await manager.stop()
