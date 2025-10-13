# from datetime import datetime, timedelta
# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
# from app.schemas.paper_trade import Trade, PaperTrading
# from app.core.database import db_paper
# from app.utils.fetch_current_prices import CoinDCXPriceFeed
# from app.coindxc_api_calls.candlesticks import CandleStick
# from app.services.paper_wallet import PaperWallet
# from app.services.symbol_service import SymbolService
# from app.utils.safe_float import safe_float
# from app.strategies import STRATEGY_REGISTRY
# from app.core.database import wallets
# import asyncio
# from app.utils.response_message import response_message, error_message
# from app.utils.serialize_doc import serialize_doc
# from app.core.auth import get_current_user
# from collections import defaultdict
# from contextlib import asynccontextmanager
# from fastapi import FastAPI

# paper_router = APIRouter(prefix="/api/paper", tags=["PaperTrading"])

# # Global state
# ws_connections = {}   
# trading_tasks = {}   
# trading_state = defaultdict(lambda: {'price': None, 'candle': None, 'last_update': datetime.utcnow()})
# symbol_service = SymbolService()

# # -----------------------------
# # Safe candle processing
# # -----------------------------
# def safe_process_candle(candle):
#     """Safely process candle data, return None if invalid"""
#     if candle is None or not isinstance(candle, dict):
#         return None
    
#     return {
#         "open": safe_float(candle.get('o')),
#         "close": safe_float(candle.get('c')),
#         "volume": safe_float(candle.get('v')),
#         "high": safe_float(candle.get('h')),
#         "low": safe_float(candle.get('l'))
#     }

# # -----------------------------
# # Trading callback
# # -----------------------------
# async def trading_callback(price=None, candle=None, wallet=None, strategy=None, qty=None, symbol=None, websocket=None):
#     user_id = wallet.user_id if wallet else None
#     if not user_id:
#         return
    
#     # Store latest data and update timestamp
#     if price is not None:
#         trading_state[user_id]['price'] = price
#         trading_state[user_id]['last_update'] = datetime.utcnow()
#         print(f"💰 Price update: {symbol} -> {price}")
        
#     if candle is not None:
#         # Safely process candle data
#         processed_candle = safe_process_candle(candle)
#         if processed_candle:
#             trading_state[user_id]['candle'] = processed_candle
#             trading_state[user_id]['last_update'] = datetime.utcnow()
#             print(f"candle_info {processed_candle}")
#         else:
#             print(f"⚠️ Invalid candle data received: {candle}")
#             return
        
#     # Only proceed if we have both price and candle
#     current_state = trading_state[user_id]
#     if current_state['price'] is None or current_state['candle'] is None:
#         return
        
#     try:
#         signal_obj = strategy.on_bar(current_state['candle'])
#         signal = getattr(signal_obj, 'action', 'HOLD')
#         current_price = current_state['price']
        
#         print(f">>> Trading: Signal={signal}, Price={current_price}")
        
#         if signal == "HOLD":
#             if websocket:
#                 try:
#                     await websocket.send_json({
#                         "type": "signal_update", 
#                         "symbol": symbol,
#                         "side": "HOLD",
#                         "current_price": current_price,
#                         "timestamp": datetime.utcnow().isoformat(),
#                         "remaining_cash": wallet.cash,
#                     })
#                 except (WebSocketDisconnect, RuntimeError) as e:
#                     print(f"WebSocket error for user {user_id}: {e}")
                    
#         elif signal == "BUY" and wallet.cash > 0:
#             # Use the qty from parameters or calculate based on wallet
#             trade_qty = qty if qty else (wallet.cash * 0.1) / current_price  # 10% of cash
#             fee = trade_qty * current_price * 0.001
            
#             await wallet.buy(symbol, current_price, trade_qty, fee)
            
#             if websocket:
#                 try:
#                     await websocket.send_json({
#                         "type": "trade_executed",
#                         "symbol": symbol,
#                         "side": "BUY",
#                         "execution_price": current_price,
#                         "quantity": trade_qty,
#                         "fee": fee,
#                         "timestamp": datetime.utcnow().isoformat(),
#                         "remaining_cash": wallet.cash,
#                         "position_size": wallet.positions.get(symbol, 0)
#                     })
#                 except (WebSocketDisconnect, RuntimeError) as e:
#                     print(f"WebSocket error for user {user_id}: {e}")

#         elif signal == "SELL" and wallet.positions.get(symbol, 0) > 0:
#             # Sell the entire position
#             trade_qty = wallet.positions.get(symbol, 0)
#             fee = trade_qty * current_price * 0.001
            
#             await wallet.sell(symbol, current_price, trade_qty, fee)
            
#             if websocket:
#                 try:
#                     await websocket.send_json({
#                         "type": "trade_executed", 
#                         "symbol": symbol,
#                         "side": "SELL",
#                         "execution_price": current_price,
#                         "quantity": trade_qty,
#                         "fee": fee,
#                         "timestamp": datetime.utcnow().isoformat(),
#                         "remaining_cash": wallet.cash,
#                         "position_size": 0  # Position closed
#                     })
#                 except (WebSocketDisconnect, RuntimeError) as e:
#                     print(f"WebSocket error for user {user_id}: {e}")
                        
#     except Exception as e:
#         print(f"Trading callback error for user {user_id}: {e}")

# # -----------------------------
# # Cleanup old users
# # -----------------------------
# async def cleanup_old_users():
#     while True:
#         try:
#             now = datetime.utcnow()
#             expired_users = [
#                 user_id for user_id, state in trading_state.items()
#                 if now - state['last_update'] > timedelta(hours=1)
#             ]
#             for user_id in expired_users:
#                 del trading_state[user_id]
#                 print(f"Cleaned up trading state for user {user_id}")
#             await asyncio.sleep(3600)  # Run every hour
#         except Exception as e:
#             print(f"Cleanup error: {e}")
#             await asyncio.sleep(60)

# # Start cleanup task
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     cleanup_task = asyncio.create_task(cleanup_old_users())
#     yield
#     cleanup_task.cancel()
#     try:
#         await cleanup_task
#     except asyncio.CancelledError:
#         pass

# # -----------------------------
# # API Endpoints
# # -----------------------------

# @paper_router.post("/trade")
# async def log_trade(trade: Trade, current_user: str = Depends(get_current_user)):
#     trade_dict = trade.dict()
#     await db_paper.get_collection("trades").insert_one(trade_dict)
#     return response_message(message="Trade logged")

# @paper_router.get("/trades/{user_id}")
# async def get_trades(user_id: str, current_user: str = Depends(get_current_user)):
#     trades = await db_paper.trades.find({"user_id": user_id}).to_list(100)
#     return response_message(message="Trades fetched successfully", data=trades) 

# @paper_router.get("/portfolio/{user_id}")
# async def get_portfolio(user_id: str, current_user: str = Depends(get_current_user)):
#     wallet = await db_paper.wallets.find_one({"user_id": str(user_id)})
#     positions = await db_paper.positions.find({"user_id": str(user_id)}).to_list(100)
#     wallet = serialize_doc(wallet)
#     positions = [serialize_doc(p) for p in positions]
#     return response_message(message="Portfolio fetched successfully", data={"wallet": wallet, "positions": positions}) 

# # -----------------------------
# # Start paper trading endpoint
# # -----------------------------
# @paper_router.post("/start_paper_trading")
# async def start_paper_trading(body: PaperTrading, current_user: str = Depends(get_current_user)):
#     user_id = body.user_id
#     symbol = body.symbol
#     qty = body.qty
#     strategy_name = body.strategy_name
#     strategy_params = body.strategy_params or {}
    
#     if user_id in trading_tasks:
#         return {"status": "already running"}
    
#     wallet_doc = await wallets.find_one({"user_id": user_id})
#     if not wallet_doc:
#         return {"status": "error", "msg": "Wallet not found for user"}
    
#     try:
#         pair = await symbol_service.get_pair_for_symbol(symbol)
#     except Exception as e:
#         return {"status": "error", "msg": f"Failed to get pair for symbol: {e}"}
    
#     wallet = PaperWallet(user_id=user_id, initial_cash=wallet_doc["cash"])
#     strategy_cls = STRATEGY_REGISTRY[strategy_name]
#     strategy = strategy_cls(strategy_params)
#     websocket = ws_connections.get(user_id)
    
#     # Initialize trading state for this user
#     trading_state[user_id] = {'price': None, 'candle': None, 'last_update': datetime.utcnow()}

#     # Create both price and candle feeds
#     price_feed = CoinDCXPriceFeed(symbol)
#     candle_feed = CandleStick(pair)
    
#     print(f"🚀 Starting paper trading for {symbol} (pair: {pair})")

#     # Register callbacks for both feeds
#     price_feed.register_callback(
#         lambda price: trading_callback(
#             price=price, 
#             wallet=wallet, 
#             strategy=strategy, 
#             qty=qty, 
#             symbol=symbol, 
#             websocket=websocket
#         )
#     )
    
#     candle_feed.register_callback(
#         lambda candle: trading_callback(
#             candle=candle, 
#             wallet=wallet, 
#             strategy=strategy, 
#             qty=qty, 
#             symbol=symbol, 
#             websocket=websocket
#         )
#     )

#     # Start both feeds
#     price_task = asyncio.create_task(price_feed.start())
#     candle_task = asyncio.create_task(candle_feed.start())
    
#     # Store both tasks
#     trading_tasks[user_id] = {
#         'price_task': price_task,
#         'candle_task': candle_task,
#         'wallet': wallet,
#         'strategy': strategy
#     }
    
#     return response_message(
#         message="Paper trading started", 
#         data={
#             "user_id": user_id, 
#             "symbol": symbol,
#             "pair": pair,
#             "strategy": strategy_name
#         }
#     )

# # -----------------------------
# # Stop paper trading endpoint
# # -----------------------------
# @paper_router.post("/stop_paper_trading")
# async def stop_paper_trading(user_id: str, current_user: str = Depends(get_current_user)):
#     if user_id not in trading_tasks:
#         return {"status": "error", "msg": "No active trading session found"}
    
#     # Cancel tasks
#     tasks = trading_tasks[user_id]
#     tasks['price_task'].cancel()
#     tasks['candle_task'].cancel()
    
#     # Clean up
#     del trading_tasks[user_id]
#     if user_id in trading_state:
#         del trading_state[user_id]
    
#     return response_message(message="Paper trading stopped", data={"user_id": user_id})

# # -----------------------------
# # Get trading status endpoint
# # -----------------------------
# @paper_router.get("/trading_status/{user_id}")
# async def get_trading_status(user_id: str, current_user: str = Depends(get_current_user)):
#     is_running = user_id in trading_tasks
#     current_state = trading_state.get(user_id, {})
    
#     return response_message(
#         message="Trading status retrieved",
#         data={
#             "is_running": is_running,
#             "has_price": current_state.get('price') is not None,
#             "has_candle": current_state.get('candle') is not None,
#             "last_update": current_state.get('last_update')
#         }
#     )

# # -----------------------------
# # Frontend WebSocket endpoint
# # -----------------------------
# @paper_router.websocket("/ws/paper_trades")
# async def websocket_endpoint(websocket: WebSocket, user_id: str):
#     await websocket.accept()
#     ws_connections[user_id] = websocket
#     print(f"🔗 WebSocket connected for user {user_id}")
#     try:
#         while True:
#             # Keep connection alive
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         ws_connections.pop(user_id, None)
#         print(f"🔗 WebSocket disconnected for user {user_id}")