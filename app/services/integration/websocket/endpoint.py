"""JWT-protected WebSocket endpoint /ws/{tenant_id}."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.logging import get_logger
from app.core.security import decode_websocket_token
from app.core.settings import settings
from app.services.integration.runtime import get_ws_manager

router = APIRouter()
logger = get_logger("pod_delta.websocket.endpoint")


@router.websocket("/ws/{tenant_id}")
async def websocket_tenant_feed(
    websocket: WebSocket,
    tenant_id: str,
    token: str | None = Query(default=None),
) -> None:
    header_token = websocket.headers.get("authorization")
    raw_token = token
    if header_token and header_token.lower().startswith("bearer "):
        raw_token = header_token.split(" ", 1)[1]

    try:
        principal = decode_websocket_token(raw_token)
    except Exception:  # noqa: BLE001
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if principal.tenant_id != tenant_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    manager = get_ws_manager()
    connection_id = await manager.connect(tenant_id, websocket)
    try:
        while True:
            try:
                incoming = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_SECONDS,
                )
                if incoming.lower() in {"ping", "heartbeat"}:
                    await manager.heartbeat(tenant_id, connection_id)
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await manager.heartbeat(tenant_id, connection_id)
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:  # noqa: BLE001
                    break
    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", tenant_id=tenant_id)
    finally:
        await manager.disconnect(tenant_id, connection_id)
