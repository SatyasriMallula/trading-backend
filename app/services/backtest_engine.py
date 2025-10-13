# app/services/backtest_engine.py
from typing import List, Dict
from datetime import datetime

def to_ts(time_val):
    """
    Convert input time to epoch seconds.
    Accepts int/float (seconds), or ISO string.
    """
    if isinstance(time_val, (int, float)):
        return int(time_val)
    try:
        return int(datetime.fromisoformat(time_val).timestamp())
    except:
        return int(datetime.utcnow().timestamp())
def run_backtest(
    candles: List[Dict],
    strategy,
    initial_capital: float = 1000.0,
    fee_rate: float = 0.001,
    position_size_pct: float = 1.0
):
    strategy.on_start({})

    cash = initial_capital
    position_qty = 0.0
    entry_price = 0.0
    entry_time = None
    entry_fee = 0.0

    trades = []
    signals = []
    equity_curve = []

    for candle in candles:
        price = float(candle["close"])
        current_time = to_ts(candle.get("time", datetime.utcnow().isoformat()))

        # Get strategy signal
        signal_result = strategy.on_bar(candle)
        signal = getattr(signal_result, 'action', "HOLD").upper()

        # Record signal for chart markers
        if signal in ["BUY", "SELL"]:
            signals.append({
                "time": current_time,
                "side": signal,
                "price": price
            })

        # --- BUY ---
        if signal == "BUY" and position_qty == 0:
            allocation = cash * position_size_pct
            position_qty = allocation / price
            entry_fee = allocation * fee_rate
            cash -= allocation + entry_fee

            entry_price = price
            entry_time = current_time
            
            # BUY Entry - Only entry information
            buy_trade = {
                "time": entry_time,
                "side": "BUY",
                "entry_price": entry_price,      # Entry price
                "entry_time": entry_time,       # Entry time
                "quantity": position_qty,       # Quantity bought
                "fee": entry_fee,               # Entry fee
                "status": "OPEN"
                # NO exit information for BUY
            }
            trades.append(buy_trade)
            
            print(f"✅ BUY executed: {position_qty:.6f} units at {price}")

        # --- SELL ---
        elif signal == "SELL" and position_qty > 0:
            trade_value = position_qty * price
            exit_fee = trade_value * fee_rate
            cash += trade_value - exit_fee

            # Calculate PnL and return
            total_investment = position_qty * entry_price
            pnl = trade_value - total_investment - (entry_fee + exit_fee)
            return_pct = (pnl / total_investment) * 100

            # SELL Entry - Only exit information + calculated results
            sell_trade = {
                "time": current_time,
                "side": "SELL", 
                "exit_price": price,            # Exit price
                "exit_time": current_time,      # Exit time
                "quantity": position_qty,       # Quantity sold
                "fee": exit_fee,               # Exit fee
                "pnl": pnl,                    # Calculated PnL
                "return_pct": return_pct,      # Calculated Return %
                "status": "CLOSED"
                # NO entry information for SELL
            }
            trades.append(sell_trade)
            
            print(f"✅ SELL executed: {position_qty:.6f} units at {price}, PnL: {pnl:.2f}")

            # Reset position
            position_qty = 0.0
            entry_price = 0.0
            entry_time = None
            entry_fee = 0.0

        # --- Equity ---
        current_equity = cash + (position_qty * price)
        equity_curve.append({
            "time": current_time,
            "value": current_equity
        })

    # Close any remaining open position at last candle
    if position_qty > 0:
        last_candle = candles[-1]
        last_price = float(last_candle["close"])
        last_time = to_ts(last_candle.get("time", datetime.utcnow().isoformat()))

        trade_value = position_qty * last_price
        exit_fee = trade_value * fee_rate
        cash += trade_value - exit_fee

        # Calculate final PnL and return
        total_investment = position_qty * entry_price
        pnl = trade_value - total_investment - (entry_fee + exit_fee)
        return_pct = (pnl / total_investment) * 100

        # Final SELL Entry
        sell_trade = {
            "time": last_time,
            "side": "SELL",
            "exit_price": last_price,
            "exit_time": last_time,
            "quantity": position_qty,
            "fee": exit_fee,
            "pnl": pnl,
            "return_pct": return_pct,
            "status": "CLOSED"
        }
        trades.append(sell_trade)

    final_balance = cash

    return {
        "final_balance": final_balance,
        "trades": trades,
        "equity_curve": equity_curve,
        "signals": signals
    }