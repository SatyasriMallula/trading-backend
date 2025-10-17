import socketio
import json
from datetime import datetime
from app.utils.response_message import response_message
from app.core.config import Settings

url = Settings().COINDCX_WEBSOCKET_URL


class CandleStick:
    def __init__(self, pair: str, timeframe: str):
        self.callbacks = []
        self.sio = socketio.AsyncClient()
        self.pair = pair
        self.timeframe = timeframe
        self.current_candle_timestamp = None
        self.last_candle = None  # Store the last candle for "completion"

        @self.sio.event
        async def connect():
            print("✅ Connected to CoinDCX socket!")
            channel = f"{self.pair}_{self.timeframe}"
            await self.sio.emit("join", {"channelName": channel})
            print(f"📡 Subscribed to: {channel}")

        @self.sio.on("candlestick")
        async def on_message(data):
            raw_json = data.get("data")
            if not raw_json:
                return

            parsed = json.loads(raw_json)
            candle_timestamp = parsed.get("t")

            # Check if this is a NEW candle
            is_new_candle = candle_timestamp != self.current_candle_timestamp

            if is_new_candle:
                # If we already had a previous candle, mark it as COMPLETE
                if self.last_candle:
                    completed_candle = {
                        **self.last_candle,
                        "is_complete": True,
                        "is_new_candle": False,
                    }

                    # ✅ Notify callbacks that the previous candle is finalized
                    for cb in self.callbacks:
                        try:
                            await cb(completed_candle)
                        except Exception as e:
                            print(f"Callback error (final candle): {e}")

                # Update current timestamp and replace last_candle
                self.current_candle_timestamp = candle_timestamp
                self.last_candle = parsed
                print(f"🆕 New candle started: {candle_timestamp}")

            else:
                # Candle still forming (5s update)
                self.last_candle = parsed
                print(f"🔄 Candle update: {candle_timestamp}")

            # Optional: also pass real-time updates to callbacks (not complete)
            live_candle = {
                **parsed,
                "is_complete": False,
                "is_new_candle": is_new_candle,
            }
            for cb in self.callbacks:
                try:
                    await cb(live_candle)
                except Exception as e:
                    print(f"Callback error (live update): {e}")

        @self.sio.event
        async def disconnect():
            print("❌ Disconnected from CoinDCX WebSocket.")
            return response_message(message="Disconnected from CoinDCX")

    def register_callback(self, cb):
        """Register async callback to receive candle data."""
        self.callbacks.append(cb)

    async def start(self):
        """Start WebSocket connection and event loop."""
        await self.sio.connect(url, transports=["websocket"])
        await self.sio.wait()
