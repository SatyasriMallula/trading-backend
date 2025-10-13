import socketio, json
from app.utils.response_message import response_message
from app.core.config import Settings
url=Settings().COINDCX_WEBSOCKET_URL
class CandleStick:
    def __init__(self,pair,timeframe):
        self.callbacks=[]
        self.sio=socketio.AsyncClient()
        self.pair=pair
        self.timeframe=timeframe
        @self.sio.event
        async def connect():
            print("I'm connected!")
            channel=f"{self.pair}_{self.timeframe}"
            await self.sio.emit('join', {'channelName': channel})

        @self.sio.on('candlestick')
        async def on_message(data):
            raw_json = data.get("data")
            print(raw_json)
            if not raw_json:
                return
            parsed = json.loads(raw_json)
            for cb in self.callbacks:
                await cb(parsed)
        
        @self.sio.event
        async def disconnect():
            return response_message(message="Disconnected from the coindcx")
        
    def register_callback(self,cb):
        self.callbacks.append(cb)


    async def start(self):
        await self.sio.connect(url, transports='websocket')
        await self.sio.wait()



