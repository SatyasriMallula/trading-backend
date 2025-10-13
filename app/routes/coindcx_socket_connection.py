from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from app.coindxc_sockets.current_prices import CurrentPrices
from app.coindxc_sockets.order_book import OrderBook
from app.coindxc_sockets.candlesticks import CandleStick
router = APIRouter(prefix="/api", tags=["coindcx_socket_connections"])

@router.websocket("/ws/current_prices")
async def current_prices(websocket: WebSocket):
    await websocket.accept()
    prices = CurrentPrices()

    # Define callback to push prices to this websocket
    async def send_to_client(price_data):
        try:
            await websocket.send_json(price_data)
        except WebSocketDisconnect:
            # Client disconnected, remove this callback
            if send_to_client in prices.callbacks:
                prices.callbacks.remove(send_to_client)

    prices.register_callback(send_to_client)

    # Start the socketio client in background
    asyncio.create_task(prices.start())

    try:
        # Keep connection alive
        while True:
            await asyncio.sleep(1)  # just keep the coroutine alive
    except WebSocketDisconnect:
        print("Client disconnected")
        if send_to_client in prices.callbacks:
            prices.callbacks.remove(send_to_client)
        websocket.close()




@router.websocket("/ws/order_book")
async def order_book(websocket: WebSocket):
    await websocket.accept()
    prices = OrderBook("B-TRX_BTC")

    # Define callback to push prices to this websocket
    async def send_to_client(price_data):
        try:
            await websocket.send_json({"data":price_data})
        except WebSocketDisconnect:
            # Client disconnected, remove this callback
            if send_to_client in prices.callbacks:
                prices.callbacks.remove(send_to_client)

    prices.register_callback(send_to_client)

    # Start the socketio client in background
    asyncio.create_task(prices.start())

    try:
        # Keep connection alive
        while True:
            await asyncio.sleep(1)  # just keep the coroutine alive
    except WebSocketDisconnect:
        print("Client disconnected")
        if send_to_client in prices.callbacks:
            prices.callbacks.remove(send_to_client)
        websocket.close()
