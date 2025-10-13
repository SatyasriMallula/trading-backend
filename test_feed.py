import socketio
import asyncio

socketEndpoint = 'wss://stream.coindcx.com'

# Async Socket.IO client
sio = socketio.AsyncClient()

@sio.event
async def connect():
    print("✅ Connected to CoinDCX!")
    await sio.emit('join', {'channelName': "B-DEP_USDT_1m"})

@sio.on('candlestick')
async def on_message(data):
    print("📈 Candle Update:")
    print(data)

@sio.event
async def disconnect():
    print("❌ Disconnected from CoinDCX")

async def main():
    try:
        # Connect to CoinDCX
        await sio.connect(socketEndpoint, transports=['websocket'])
        # Keep the connection alive
        await sio.wait()
    except Exception as e:
        print(f"Error connecting to the server: {e}")
        raise

# Run async main
if __name__ == '__main__':
    asyncio.run(main())

# {
#   "user_id": "user2",
#   "symbol": "INJUSDT",
#   "amount": 10000,
#   "strategy_name": "sma_crossover",
#   "strategy_params": {
#     "short": 10,
#     "long": 30,
#     "period": 0
#   }
# }