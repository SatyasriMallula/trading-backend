import socketio,json
from app.utils.response_message import response_message
from app.core.config import Settings
url=Settings().COINDCX_WEBSOCKET_URL
class OrderBook:
    def __init__(self,pair):
        self.callbacks=[]
        self.sio=socketio.AsyncClient()
        self.pair=pair

        @self.sio.event
        async def connect():
            print("I'm connected!")
            await self.sio.emit('join', {'channelName': f'{self.pair}@orderbook@10'})

        @self.sio.on('depth-snapshot')
        async def on_message(data):
            print("sjdsjdsd",data)
            raw_json = data.get("data")
            if not raw_json:
                return
            parsed = json.loads(raw_json)  
            price_data = parsed.get("prices", {})
            print(price_data)
            if price_data:
                # Notify all registered callbacks
                for cb in self.callbacks:
                    await cb(price_data)
        
        @self.sio.event
        async def disconnect():
            return response_message(message="Disconnected from the coindcx")
        
    def register_callback(self,cb):
        self.callbacks.append(cb)


    async def start(self):
        await self.sio.connect(url, transports='websocket')
        await self.sio.wait()



