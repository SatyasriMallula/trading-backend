# app/services/trading_manager.py
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Dict, Any

class TradingManager:
    def __init__(self):
        self.ws_connections = {}
        self.trading_tasks = {}
        self.trading_state = defaultdict(lambda: {'price': None, 'candle': None, 'last_update': datetime.utcnow()})
        self.trading_sessions = {}
        self.market_hours = {
            'start': timedelta(hours=9, minutes=15),
            'end': timedelta(hours=15, minutes=30)
        }
    
    async def add_websocket_connection(self, user_id: str, websocket):
        """Add WebSocket connection and handle reconnection"""
        self.ws_connections[user_id] = websocket
        print(f"🔗 WebSocket connected for user {user_id}")
        
        # Send immediate status update
        if self.is_trading_active(user_id):
            await self._send_connection_status(user_id, websocket)
    
    async def _send_connection_status(self, user_id: str, websocket):
        """Send current trading status to WebSocket"""
        try:
            current_state = self.get_trading_state(user_id)
            await websocket.send_json({
                "type": "connection_established",
                "message": "Connected to running trading session",
                "has_price": current_state.get('price') is not None,
                "has_candle": current_state.get('candle') is not None,
                "last_update": current_state.get('last_update'),
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"Error sending connection status: {e}")
    
    def get_websocket(self, user_id: str):
        """Get WebSocket connection if it exists and is connected"""
        return self.ws_connections.get(user_id)
    
    async def send_websocket_message(self, user_id: str, message: dict):
        """Safely send message to WebSocket"""
        websocket = self.get_websocket(user_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"WebSocket send error for user {user_id}: {e}")
                # Remove disconnected WebSocket
                self.ws_connections.pop(user_id, None)
    
    async def start_trading(self, user_id: str, tasks_data: dict):
        """Start trading tasks for user"""
        self.trading_tasks[user_id] = tasks_data
        self.trading_sessions[user_id] = {
            'started_at': datetime.utcnow(),
            'symbol': tasks_data.get('symbol'),
            'strategy': tasks_data.get('strategy_name')
        }
        print(f"🚀 Trading session started for user {user_id}")
        
        # Notify WebSocket if connected
        await self.send_websocket_message(user_id, {
            "type": "trading_started",
            "message": "Trading session started",
            "symbol": tasks_data.get('symbol'),
            "strategy": tasks_data.get('strategy_name'),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def stop_trading(self, user_id: str):
        """Stop trading only when explicitly requested"""
        if user_id in self.trading_tasks:
            tasks = self.trading_tasks[user_id]
            tasks['price_task'].cancel()
            tasks['candle_task'].cancel()
            
            try:
                await asyncio.gather(
                    tasks['price_task'],
                    tasks['candle_task'],
                    return_exceptions=True
                )
            except asyncio.CancelledError:
                pass
            
            del self.trading_tasks[user_id]
        
        if user_id in self.trading_sessions:
            session = self.trading_sessions[user_id]
            session['ended_at'] = datetime.utcnow()
            print(f"🛑 Trading session ended for user {user_id}")
        
        # Notify WebSocket if connected
        await self.send_websocket_message(user_id, {
            "type": "trading_stopped",
            "message": "Trading session stopped",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def is_trading_active(self, user_id: str) -> bool:
        return user_id in self.trading_tasks
    
    def update_trading_state(self, user_id: str, price=None, candle=None):
        if price is not None:
            self.trading_state[user_id]['price'] = price
            self.trading_state[user_id]['last_update'] = datetime.utcnow()
            
        if candle is not None:
            self.trading_state[user_id]['candle'] = candle
            self.trading_state[user_id]['last_update'] = datetime.utcnow()
    
    def get_trading_state(self, user_id: str) -> dict:
        return self.trading_state.get(user_id, {})
    
    def is_market_hours(self) -> bool:
        now = datetime.utcnow()
        ist_now = now + timedelta(hours=5, minutes=30)
        current_time = timedelta(hours=ist_now.hour, minutes=ist_now.minute)
        return self.market_hours['start'] <= current_time <= self.market_hours['end']
    
    async def cleanup_old_users(self):
        while True:
            try:
                now = datetime.utcnow()
                expired_users = [
                    user_id for user_id, state in self.trading_state.items()
                    if now - state['last_update'] > timedelta(hours=24)
                ]
                
                for user_id in expired_users:
                    if not self.is_market_hours():
                        await self.stop_trading(user_id)
                        print(f"🧹 Cleaned up very old user {user_id} (24h+ inactive)")
                
                await asyncio.sleep(3600)
            except Exception as e:
                print(f"Cleanup error: {e}")
                await asyncio.sleep(60)
    
    def get_active_sessions(self) -> Dict[str, Any]:
        return {
            user_id: {
                **session,
                'running_time': str(datetime.utcnow() - session['started_at']),
                'has_websocket': user_id in self.ws_connections
            }
            for user_id, session in self.trading_sessions.items()
            if user_id in self.trading_tasks
        }

# Global instance
trading_manager = TradingManager()