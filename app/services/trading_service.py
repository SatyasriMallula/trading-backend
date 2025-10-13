# app/services/trading_service.py
from datetime import datetime
from app.services.trading_manager import trading_manager
from app.utils.safe_float import safe_float
from app.coindxc_sockets.current_prices import CurrentPrices
from app.coindxc_sockets.candlesticks import CandleStick
from app.services.paper_wallet import PaperWallet
from app.services.symbol_service import SymbolService
from app.strategies import STRATEGY_REGISTRY
from app.core.database import wallets
import asyncio


class TradingService:
    def __init__(self):
        self.symbol_service = SymbolService()
        # {(user_id, symbol): last_processed_candle_timestamp}
        self.last_candle_time = {}

    def safe_process_candle(self, candle):
        """Ensure candle data is valid and converted to float safely."""
        if candle is None or not isinstance(candle, dict):
            return None

        def to_float(value):
            try:
                return float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                return 0.0

        candle_timestamp = candle.get("t")

        return {
            "time": candle_timestamp // 1000 if candle_timestamp else None,
            "open": to_float(candle.get("o")),
            "close": to_float(candle.get("c")),
            "high": to_float(candle.get("h")),
            "low": to_float(candle.get("l")),
            "volume": to_float(candle.get("v")),
            "timestamp": candle_timestamp,
        }

    async def trading_callback(
        self, price=None, candle=None, wallet=None, strategy=None, qty=None, symbol=None, user_id=None
    ):
        if not user_id or not symbol:
            return

        # ---------------- PRICE UPDATE ----------------
        if price is not None:
            trading_manager.update_trading_state(user_id, price=price)
            print(f"💰 Price update: {symbol} -> {price}")

            await trading_manager.send_websocket_message(
                user_id,
                {
                    "type": "price_update",
                    "symbol": symbol,
                    "price": price,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                },
            )

        # ---------------- CANDLE UPDATE ----------------
        if candle is not None:
            processed_candle = self.safe_process_candle(candle)
            if not processed_candle:
                print(f"⚠️ Invalid candle data received: {candle}")
                return

            candle_timestamp = processed_candle.get("timestamp")
            key = (user_id, symbol)
            last_time = self.last_candle_time.get(key)

            # 🚫 Skip duplicate / same candle updates
            if last_time == candle_timestamp:
                return

            # ✅ New candle arrived
            self.last_candle_time[key] = candle_timestamp

            trading_manager.update_trading_state(user_id, candle=processed_candle)
            print(f"📊 Candle update: {symbol} -> {processed_candle}")

            await trading_manager.send_websocket_message(
                user_id,
                {
                    "type": "candle_update",
                    "symbol": symbol,
                    "candle": {k: v for k, v in processed_candle.items() if k != "timestamp"},
                    "timestamp": candle_timestamp,
                },
            )

        # ---------------- STRATEGY EXECUTION ----------------
        current_state = trading_manager.get_trading_state(user_id)
        if not current_state.get("price") or not current_state.get("candle"):
            return

        try:
            signal_obj = strategy.on_bar(current_state["candle"])
            signal = getattr(signal_obj, "action", "HOLD")
            current_price = current_state["price"]

            # Only act when the signal is BUY or SELL
            if signal not in ("BUY", "SELL"):
                print(f"📉 {symbol} -> HOLD (no action)")
                return

            print(f"📈 Strategy: {symbol} -> Signal={signal}, Price={current_price}")

            await trading_manager.send_websocket_message(
                user_id,
                {
                    "type": "signal_update",
                    "symbol": symbol,
                    "signal": signal,
                    "price": current_price,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                },
            )

            # Execute orders
            if signal == "BUY" and wallet.available_balance > 0:
                await self._execute_buy(user_id, symbol, current_price, wallet, qty)
            elif signal == "SELL" and wallet.positions.get(symbol, 0) > 0:
                await self._execute_sell(user_id, symbol, current_price, wallet, qty)

        except Exception as e:
            print(f"❌ Trading callback error for user {user_id}: {e}")

    async def _send_hold_signal(self, user_id: str, symbol: str, current_price: float, wallet):
        """Send HOLD signal to frontend (optional if needed later)."""
        await trading_manager.send_websocket_message(
            user_id,
            {
                "type": "signal_update",
                "symbol": symbol,
                "side": "HOLD",
                "current_price": current_price,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "available_balance": wallet.available_balance,
                "total_balance": wallet.total_balance,
            },
        )

    async def _execute_buy(self, user_id: str, symbol: str, current_price: float, wallet, qty):
        """Execute BUY order."""
        trade_qty = qty if qty else (wallet.available_balance * 0.1) / current_price
        fee = trade_qty * current_price * 0.001

        success = await wallet.buy(symbol, current_price, trade_qty, fee)

        if success:
            await trading_manager.send_websocket_message(
                user_id,
                {
                    "type": "trade_executed",
                    "symbol": symbol,
                    "side": "BUY",
                    "execution_price": current_price,
                    "quantity": trade_qty,
                    "fee": fee,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "available_balance": wallet.available_balance,
                    "total_balance": wallet.total_balance,
                    "position_size": wallet.positions.get(symbol, 0),
                },
            )
        else:
            await trading_manager.send_websocket_message(
                user_id,
                {
                    "type": "trade_failed",
                    "symbol": symbol,
                    "side": "BUY",
                    "reason": "Insufficient balance",
                    "timestamp": int(datetime.now().timestamp() * 1000),
                },
            )

    async def _execute_sell(self, user_id: str, symbol: str, current_price: float, wallet, qty):
        """Execute SELL order."""
        current_position = wallet.positions.get(symbol, 0)
        trade_qty = qty if qty and qty <= current_position else current_position

        if trade_qty <= 0:
            return

        fee = trade_qty * current_price * 0.001
        success = await wallet.sell(symbol, current_price, trade_qty, fee)

        if success:
            await trading_manager.send_websocket_message(
                user_id,
                {
                    "type": "trade_executed",
                    "symbol": symbol,
                    "side": "SELL",
                    "execution_price": current_price,
                    "quantity": trade_qty,
                    "fee": fee,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "available_balance": wallet.available_balance,
                    "total_balance": wallet.total_balance,
                    "position_size": wallet.positions.get(symbol, 0),
                },
            )
        else:
            await trading_manager.send_websocket_message(
                user_id,
                {
                    "type": "trade_failed",
                    "symbol": symbol,
                    "side": "SELL",
                    "reason": "Insufficient position",
                    "timestamp": int(datetime.now().timestamp() * 1000),
                },
            )

    async def start_paper_trading(self, user_id: str, symbol: str, qty: float, strategy_name: str, timeframe: str, strategy_params: dict):
        """Start simulated paper trading."""
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

        price_feed = CurrentPrices(symbol)
        candle_feed = CandleStick(pair, timeframe)

        print(f"🚀 Starting paper trading for {symbol} (pair: {pair}) with balance: {available_balance}")

        price_feed.register_callback(
            lambda price: asyncio.create_task(
                self.trading_callback(
                    price=price,
                    wallet=wallet,
                    strategy=strategy,
                    qty=qty,
                    symbol=symbol,
                    user_id=user_id,
                )
            )
        )

        candle_feed.register_callback(
            lambda candle: asyncio.create_task(
                self.trading_callback(
                    candle=candle,
                    wallet=wallet,
                    strategy=strategy,
                    qty=qty,
                    symbol=symbol,
                    user_id=user_id,
                )
            )
        )

        price_task = asyncio.create_task(price_feed.start())
        candle_task = asyncio.create_task(candle_feed.start())

        await trading_manager.start_trading(
            user_id,
            {
                "price_task": price_task,
                "candle_task": candle_task,
                "wallet": wallet,
                "strategy": strategy,
                "symbol": symbol,
                "strategy_name": strategy_name,
                "timeframe": timeframe,
            },
        )

        return {
            "status": "success",
            "user_id": user_id,
            "symbol": symbol,
            "pair": pair,
            "strategy": strategy_name,
            "available_balance": available_balance,
        }


# Global instance
trading_service = TradingService()
