import socketio, asyncio, json
from app.core.config import Settings

url = Settings().COINDCX_WEBSOCKET_URL

class CurrentPrices:
     def __init__(self, symbol):
        self.symbol = symbol
        self.callbacks = []
        self.sio = socketio.AsyncClient()

        @self.sio.event
        async def connect():
            print("✅ Connected to CoinDCX!")
            await self.sio.emit('join', {'channelName': "currentPrices@spot@10s"})

        @self.sio.on('currentPrices@spot#update')
        async def on_message(data):
            raw_json = data.get("data")
            if not raw_json:
                return
            parsed = json.loads(raw_json)  # convert string -> dict
            price_data = parsed.get("prices", {})
            price = price_data.get(self.symbol)
            if price is not None:
                print(f"📈 {self.symbol} -> {price}")
                for cb in self.callbacks:
                    await cb(price)
        @self.sio.event
        async def disconnect():
            print("❌ Disconnected from CoinDCX")

     def register_callback(self, callback):
        self.callbacks.append(callback)

     async def start(self):
        await self.sio.connect(url, transports=['websocket'])
        await self.sio.wait()