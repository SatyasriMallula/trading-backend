# app/services/trading_service.py
from datetime import datetime
from app.services.trading_manager import trading_manager
from app.utils.safe_float import safe_float
from app.coindxc_sockets.candlesticks import CandleStick
from app.services.paper_wallet import PaperWallet
from app.services.symbol_service import SymbolService
from app.strategies import STRATEGY_REGISTRY
from app.core.database import wallets
import asyncio

class TradingService:
    def __init__(self):
        self.symbol_service = SymbolService()
    
    def safe_process_candle(self, candle):
        if candle is None or not isinstance(candle, dict):
            return None

        def to_float(value):
            try:
                return float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                return 0.0

        candle_timestamp = candle.get('t')

        return {
            "time": candle_timestamp // 1000 if candle_timestamp else None,
            "open": to_float(candle.get('o')),
            "close": to_float(candle.get('c')),
            "volume": to_float(candle.get('v')),
            "high": to_float(candle.get('h')),
            "low": to_float(candle.get('l')),
            "timestamp": candle_timestamp
        }

    async def trading_callback(self, candle=None, wallet=None, strategy=None, qty=None, symbol=None, user_id=None):
        if not user_id:
            return

        if candle is not None:
            processed_candle = self.safe_process_candle(candle)
            if processed_candle:
                trading_manager.update_trading_state(user_id, candle=processed_candle)
                print(f"📊 Candle update: {symbol} -> {processed_candle}")

                candle_timestamp = processed_candle.get('timestamp')
                candle_data = {k: v for k, v in processed_candle.items() if k != 'timestamp'}

                await trading_manager.send_websocket_message(user_id, {
                    "type": "candle_update",
                    "symbol": symbol,
                    "candle": candle_data,
                    "timestamp": candle_timestamp
                })
            else:
                print(f"⚠️ Invalid candle data received: {candle}")
                return
        if candle["is_complete"]:
            current_state = trading_manager.get_trading_state(user_id)
            if current_state.get('candle') is None:
                return

            try:
                signal_obj = strategy.on_bar(current_state['candle'])
                signal = getattr(signal_obj, 'action', '')
                current_price = current_state['candle']['close']

                print(f">>> Trading: Signal={signal}, Price={current_price}")

                await trading_manager.send_websocket_message(user_id, {
                "type": "signal_update",
                "symbol": symbol,
                "side": signal,
                "price": current_price,
                "timestamp": int(datetime.now().timestamp() * 1000)
            })
                if signal == "BUY" and wallet.available_balance > 0:
                    await self._execute_buy(user_id, symbol, current_price, wallet, qty)

                elif signal == "SELL" and wallet.positions.get(symbol, 0) > 0:
                    await self._execute_sell(user_id, symbol, current_price, wallet, qty)

            except Exception as e:
                print(f"Trading callback error for user {user_id}: {e}")

    async def _execute_buy(self, user_id: str, symbol: str, current_price: float, wallet, qty:float):
        if qty:
            trade_qty = qty
        else:
            trade_qty = (wallet.available_balance * 0.1) / current_price

        fee = trade_qty * current_price * 0.001
        success = await wallet.buy(symbol, current_price, trade_qty, fee)

        if success:
            await trading_manager.send_websocket_message(user_id, {
                "type": "trade_executed",
                "symbol": symbol,
                "side": "BUY",
                "execution_price": current_price,
                "quantity": trade_qty,
                "fee": fee,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "available_balance": wallet.available_balance,
                "total_balance": wallet.total_balance,
                "position_size": wallet.positions.get(symbol, 0)
            })
        else:
            await trading_manager.send_websocket_message(user_id, {
                "type": "trade_failed",
                "symbol": symbol,
                "side": "BUY",
                "reason": "Insufficient balance",
                "timestamp": int(datetime.now().timestamp() * 1000)
            })

    async def _execute_sell(self, user_id: str, symbol: str, current_price: float, wallet, qty):
        current_position = wallet.positions.get(symbol, 0)

        if qty and qty <= current_position:
            trade_qty = qty
        else:
            trade_qty = current_position

        if trade_qty <= 0:
            return

        fee = trade_qty * current_price * 0.001
        success = await wallet.sell(symbol, current_price, trade_qty, fee)

        if success:
            await trading_manager.send_websocket_message(user_id, {
                "type": "trade_executed",
                "symbol": symbol,
                "side": "SELL",
                "execution_price": current_price,
                "quantity": trade_qty,
                "fee": fee,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "available_balance": wallet.available_balance,
                "total_balance": wallet.total_balance,
                "position_size": wallet.positions.get(symbol, 0)
            })
        else:
            await trading_manager.send_websocket_message(user_id, {
                "type": "trade_failed",
                "symbol": symbol,
                "side": "SELL",
                "reason": "Insufficient position",
                "timestamp": int(datetime.now().timestamp() * 1000)
            })

    async def start_paper_trading(self, user_id: str, symbol: str, qty: float, strategy_name: str, timeframe: str, strategy_params: dict):
        if trading_manager.is_trading_active(user_id):
            return {"status": "error", "msg": "Trading already running"}

        wallet_doc = await wallets.find_one({"user_id": user_id})
        if not wallet_doc:
            return {"status": "error", "msg": "Wallet not found for user"}

        available_balance = wallet_doc.get("available_balance", 0)
        if available_balance <= 0:
            return {"status": "error", "msg": "Insufficient available balance"}

        try:
            pair = await self.symbol_service.get_pair_for_symbol(symbol)
        except Exception as e:
            return {"status": "error", "msg": f"Failed to get pair for symbol: {e}"}

        wallet = PaperWallet(user_id=user_id, initial_cash=available_balance)
        strategy_cls = STRATEGY_REGISTRY[strategy_name]
        strategy = strategy_cls(strategy_params)

        trading_manager.update_trading_state(user_id)

        candle_feed = CandleStick(pair, timeframe)

        print(f"🚀 Starting paper trading for {symbol} (pair: {pair}) with available balance: {available_balance}")

        candle_feed.register_callback(
            lambda candle: asyncio.create_task(self.trading_callback(
                candle=candle,
                wallet=wallet,
                strategy=strategy,
                qty=qty,
                symbol=symbol,
                user_id=user_id
            ))
        )

        candle_task = asyncio.create_task(candle_feed.start())

        await trading_manager.start_trading(user_id, {
            'candle_task': candle_task,
            'wallet': wallet,
            'strategy': strategy,
            'symbol': symbol,
            'strategy_name': strategy_name,
            'timeframe': timeframe
        })

        return {
            "status": "success",
            "user_id": user_id,
            "symbol": symbol,
            "pair": pair,
            "strategy": strategy_name,
            "available_balance": available_balance
        }

# Global instance
trading_service = TradingService()
