from typing import Dict, Set
from fastapi import WebSocket
import json

class ClientManager:
    def __init__(self):
        self.clients: Dict[WebSocket, Dict[str, list]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients[websocket] = {}

    def disconnect(self, websocket: WebSocket):
        self.clients.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, channel: str, symbols: list):
        self.clients[websocket].setdefault(channel, [])
        for s in symbols:
            if s not in self.clients[websocket][channel]:
                self.clients[websocket][channel].append(s)

    def unsubscribe(self, websocket: WebSocket, channel: str, symbols: list):
        if channel in self.clients[websocket]:
            self.clients[websocket][channel] = [
                s for s in self.clients[websocket][channel] if s not in symbols
            ]

    def get_backend_channels(self):
        """Return combined subscriptions for CoinDCX."""
        backend_channels = {}
        for sub in self.clients.values():
            for ch, symbols in sub.items():
                backend_channels.setdefault(ch, set()).update(symbols)
        return [{"name": ch, "symbols": list(symbols)} for ch, symbols in backend_channels.items() if symbols]

    async def broadcast(self, topic: str, data: dict):
        dead_clients = []
        for ws, subs in self.clients.items():
            if topic in subs:
                client_symbols = subs[topic]
                filtered_data = [d for d in data.get("data", []) if d["s"] in client_symbols]
                if filtered_data:
                    out = data.copy()
                    out["data"] = filtered_data
                    try:
                        await ws.send_text(json.dumps(out))
                    except:
                        dead_clients.append(ws)
        for ws in dead_clients:
            self.disconnect(ws)


client_manager = ClientManager()
