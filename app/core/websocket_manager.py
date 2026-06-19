import uuid
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        # user_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    def is_connected(self, user_id: uuid.UUID) -> bool:
        return bool(self._connections.get(str(user_id)))

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        uid = str(user_id)
        if uid not in self._connections:
            self._connections[uid] = []
        self._connections[uid].append(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        uid = str(user_id)
        if uid in self._connections:
            self._connections[uid] = [
                ws for ws in self._connections[uid] if ws != websocket
            ]
            if not self._connections[uid]:
                del self._connections[uid]

    async def send(self, user_id: uuid.UUID, message: str) -> None:
        uid = str(user_id)
        dead = []
        for ws in self._connections.get(uid, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast(self, message: str) -> None:
        for uid, connections in list(self._connections.items()):
            for ws in connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    pass


# Singleton — один на всё приложение
ws_manager = WebSocketManager()