"""Client websocket registry + broadcast helper. Each client must supply a device name before it counts as
connected; only one of them may be the listener (streaming audio) at a time."""
import json
from dataclasses import dataclass

from fastapi import WebSocket


@dataclass
class Client:
    device_name: str
    ws: WebSocket
    wants_live_audio: bool = False  # opt-in "play live audio" subscription


class WsManager:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, Client] = {}
        self.listener_ws: WebSocket | None = None

    def device_names(self) -> list[str]:
        return [c.device_name for c in self.clients.values()]

    def register(self, ws: WebSocket, device_name: str) -> None:
        self.clients[ws] = Client(device_name=device_name, ws=ws)

    def unregister(self, ws: WebSocket) -> None:
        self.clients.pop(ws, None)
        if self.listener_ws is ws:
            self.listener_ws = None

    def set_live_audio_wanted(self, ws: WebSocket, wanted: bool) -> None:
        if ws in self.clients:
            self.clients[ws].wants_live_audio = wanted

    async def broadcast(self, type_: str, payload: dict) -> None:
        message = json.dumps({"type": type_, "payload": payload})
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)

    async def send_to(self, ws: WebSocket, type_: str, payload: dict) -> None:
        await ws.send_text(json.dumps({"type": type_, "payload": payload}))

    async def broadcast_binary_to_live_audio_subscribers(self, data: bytes) -> None:
        dead = []
        for ws, client in list(self.clients.items()):
            if not client.wants_live_audio:
                continue
            try:
                await ws.send_bytes(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)


manager = WsManager()
