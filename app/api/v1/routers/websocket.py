import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.websocket_manager import ws_manager
from app.infrastructure.db.session import get_db
from app.infrastructure.redis.client import redis_client

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    # Auth via JWT token query param
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    import uuid
    user_id = uuid.UUID(payload.get("sub"))

    await ws_manager.connect(user_id, websocket)

    # Send queued offline notifications
    queue_key = f"notifications:offline:{user_id}"
    while True:
        item = await redis_client.rpop(queue_key)
        if not item:
            break
        await websocket.send_text(item)

    try:
        while True:
            # Keep connection alive — wait for any message (ping)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)