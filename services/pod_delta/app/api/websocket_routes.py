"""JWT-protected tenant WebSocket endpoint."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, status
from starlette.websockets import WebSocketDisconnect

from app.core.security import decode_websocket_token
from app.core.settings import settings
from app.integration.runtime import get_websocket_manager

router = APIRouter()


@router.websocket("/ws/{tenant_id}")
async def websocket_tenant_feed(
    websocket: WebSocket,
    tenant_id: str,
    token: str | None = Query(default=None),
) -> None:
    authorization = websocket.headers.get("authorization")
    raw_token = token
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ", 1)[1]

    try:
        principal = decode_websocket_token(raw_token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if principal.tenant_id != tenant_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    manager = get_websocket_manager()
    connection_id = await manager.connect(tenant_id, websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_SECONDS,
                )
                if message.lower() in {"ping", "heartbeat"}:
                    await manager.heartbeat(tenant_id, connection_id)
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await manager.heartbeat(tenant_id, connection_id)
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(tenant_id, connection_id)

