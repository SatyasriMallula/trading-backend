# app/routes/paper_trading.py
from fastapi import APIRouter, WebSocket, Depends
from app.schemas.paper_trade import Trade, PaperTrading
from app.core.database import db_paper
from app.services.trading_manager import trading_manager
from app.services.trading_service import trading_service
from app.utils.response_message import response_message, error_message
from app.utils.serialize_doc import serialize_doc
from app.core.auth import get_current_user

paper_router = APIRouter(prefix="/api/paper", tags=["PaperTrading"])

@paper_router.post("/trade")
async def log_trade(trade: Trade, current_user: str = Depends(get_current_user)):
    trade_dict = trade.dict()
    await db_paper.get_collection("trades").insert_one(trade_dict)
    return response_message(message="Trade logged")
@paper_router.get("/trading_state/{user_id}")
async def get_trading_state(user_id: str):
    try:
        result = await trading_service.get_trading_state(user_id)
        return result
    except Exception as e:
        return {"status": "error", "msg": str(e)}
@paper_router.get("/trades/{user_id}")
async def get_trades(user_id: str, current_user: str = Depends(get_current_user)):
    trades = await db_paper.trades.find({"user_id": user_id}).to_list(100)
    return response_message(message="Trades fetched successfully", data=trades) 

@paper_router.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str, current_user: str = Depends(get_current_user)):
    wallet = await db_paper.wallets.find_one({"user_id": str(user_id)})
    positions = await db_paper.positions.find({"user_id": str(user_id)}).to_list(100)
    wallet = serialize_doc(wallet)
    positions = [serialize_doc(p) for p in positions]
    return response_message(message="Portfolio fetched successfully", data={"wallet": wallet, "positions": positions}) 

@paper_router.post("/start_paper_trading")
async def start_paper_trading(body: PaperTrading, current_user: str = Depends(get_current_user)):
    """Start paper trading - will run continuously until manually stopped"""
    result = await trading_service.start_paper_trading(
        user_id=body.user_id,
        symbol=body.symbol,
        timeframe=body.timeframe,
        qty=body.qty,
        strategy_name=body.strategy_name,
        strategy_params=body.strategy_params or {}
    )
    
    if result.get("status") == "error":
        return error_message(message=result["msg"])
    
    return response_message(
        message="Paper trading started - will run continuously until manually stopped", 
        data=result
    )

from pydantic import BaseModel

class StopPaperTradingRequest(BaseModel):
    user_id: str

@paper_router.post("/stop_paper_trading")
async def stop_paper_trading(body: StopPaperTradingRequest, current_user: str = Depends(get_current_user)):
    """MANUALLY stop paper trading"""
    await trading_manager.stop_trading(body.user_id)
    return response_message(message="Paper trading manually stopped", data={"user_id": body.user_id})

@paper_router.get("/trading_status/{user_id}")
async def get_trading_status(user_id: str, current_user: str = Depends(get_current_user)):
    """Get trading status with connection info"""
    is_running = trading_manager.is_trading_active(user_id)
    current_state = trading_manager.get_trading_state(user_id)
    has_websocket = user_id in trading_manager.ws_connections
    
    return response_message(
        message="Trading status retrieved",
        data={
            "is_running": is_running,
            "has_websocket": has_websocket,
            "has_price": current_state.get('price') is not None,
            "has_candle": current_state.get('candle') is not None,
            "last_update": current_state.get('last_update'),
            "market_hours": trading_manager.is_market_hours()
        }
    )

@paper_router.get("/active_sessions")
async def get_active_sessions(current_user: str = Depends(get_current_user)):
    """Get all active trading sessions (admin view)"""
    active_sessions = trading_manager.get_active_sessions()
    return response_message(
        message="Active sessions retrieved",
        data={
            "total_sessions": len(active_sessions),
            "sessions": active_sessions
        }
    )

# app/routes/paper_trading.py (only showing the WebSocket endpoint)
@paper_router.websocket("/ws/paper_trades/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    # Add WebSocket connection
    await trading_manager.add_websocket_connection(user_id, websocket)
    
    try:
        # Keep the connection alive and handle messages
        while True:
            # Wait for any message from client (ping, etc.)
            data = await websocket.receive_text()
            
            # Optional: Handle client messages
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "status":
                # Send current status
                is_running = trading_manager.is_trading_active(user_id)
                current_state = trading_manager.get_trading_state(user_id)
                await websocket.send_json({
                    "type": "status_response",
                    "is_running": is_running,
                    "has_candle": current_state.get('candle') is not None,
                    "last_update": current_state.get('last_update')
                })
                
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
    finally:
        # Clean up on disconnect
        trading_manager.ws_connections.pop(user_id, None)
        print(f"🔗 WebSocket disconnected for user {user_id}")