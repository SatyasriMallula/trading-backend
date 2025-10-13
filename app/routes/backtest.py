# app/routes/backtest.py
from fastapi import APIRouter, HTTPException
from app.strategies import STRATEGY_REGISTRY
from app.coindcx_rest_apis.fetch_candles import fetch_coindcx_candles
from app.services.backtest_engine import run_backtest
from app.schemas.backtest import BacktestRequest
from app.utils.response_message import response_message
from app.utils.safe_float import safe_float
import numpy as np
from datetime import datetime

backtest_router = APIRouter(prefix="/api", tags=["BackTesting"])


@backtest_router.post("/backtest")
async def run_backtest_endpoint(body: BacktestRequest):
    # 1️⃣ Fetch candle data
    candle_params = body.candle_params
    candles = fetch_coindcx_candles(
        candle_params.pair,
        candle_params.interval,
        candle_params.limit,
        candle_params.startTime,
        candle_params.endTime
    )

    if not candles:
        raise HTTPException(502, "No candles fetched")

    # 2️⃣ Load strategy and run backtest
    strategy_cls = STRATEGY_REGISTRY.get(body.strategy)
    if not strategy_cls:
        raise HTTPException(400, f"Unknown strategy '{body.strategy}'")

    strategy = strategy_cls(body.params)
    result = run_backtest(
        candles,
        strategy,
        body.initial_capital,
        body.fee_rate,
        body.position_size_pct,
    )
    
    trades = result.get("trades", [])
    equity_curve_raw = result.get("equity_curve", [])
    final_balance = result.get("final_balance", body.initial_capital)
    signals = result.get("signals", [])
    
    # 3️⃣ Normalize equity_curve
    equity_curve = []
    if len(equity_curve_raw) > 0:
        if isinstance(equity_curve_raw[0], dict) and "value" in equity_curve_raw[0]:
            equity_curve = equity_curve_raw
            equity_values = [pt["value"] for pt in equity_curve]
        else:  # assume list of floats
            equity_values = equity_curve_raw
            # assign timestamps based on candle times for proper equity curve
            if candles and len(candles) == len(equity_values):
                equity_curve = [
                    {"time": candles[i]["time"], "value": v} for i, v in enumerate(equity_values)
                ]
            else:
                equity_curve = [
                    {"time": datetime.utcnow().isoformat(), "value": v} for v in equity_values
                ]
    else:
        equity_values = [body.initial_capital]
        equity_curve = [{"time": datetime.utcnow().isoformat(), "value": body.initial_capital}]

    # 4️⃣ Compute analytics
    initial_balance = body.initial_capital
    total_return = ((final_balance - initial_balance) / initial_balance) * 100
    net_profit = final_balance - initial_balance

    total_trades = len(trades)
    pnl_list = [t.get("pnl", 0) or t.get("realized_pnl", 0) for t in trades]

    winning_trades = [p for p in pnl_list if p > 0]
    losing_trades = [p for p in pnl_list if p <= 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades else 0

    # Max drawdown
    peak, max_drawdown = equity_values[0], 0
    for v in equity_values:
        if v > peak:
            peak = v
        drawdown = (peak - v) / peak
        max_drawdown = max(max_drawdown, drawdown)

    # Volatility & Sharpe
    returns = np.diff(equity_values) / equity_values[:-1] if len(equity_values) > 1 else [0]
    mean_return = np.mean(returns) if len(returns) > 0 else 0
    std_return = np.std(returns) if len(returns) > 0 else 0
    sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
    
    # Profit factor with safe division
    total_wins = sum(winning_trades) if winning_trades else 0
    total_losses = abs(sum(losing_trades)) if losing_trades else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

    # CAGR
    if len(equity_curve) >= 2:
        try:
            start_time = datetime.fromisoformat(equity_curve[0]["time"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(equity_curve[-1]["time"].replace('Z', '+00:00'))
            years = max((end_time - start_time).days / 365, 0.01)
            cagr = ((final_balance / initial_balance) ** (1 / years) - 1) * 100 if years > 0 else 0
        except:
            cagr = 0
    else:
        cagr = 0

    # Trade streaks & avg holding time
    longest_win_streak = longest_loss_streak = cur_win = cur_loss = 0
    holding_times = []

    for t in trades:
        pnl = t.get("pnl", 0) or t.get("realized_pnl", 0)
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
        else:
            cur_loss += 1
            cur_win = 0
        longest_win_streak = max(longest_win_streak, cur_win)
        longest_loss_streak = max(longest_loss_streak, cur_loss)

        # Handle different timestamp field names
        entry_time = t.get("entry_time") or t.get("time")
        exit_time = t.get("exit_time")
        if entry_time and exit_time:
            try:
                start = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                holding_times.append((end - start).total_seconds() / 3600)
            except:
                pass

    avg_holding_time = f"{round(np.mean(holding_times), 2)}h" if holding_times else "0h"

    # Calculate additional metrics for frontend
    avg_win = np.mean(winning_trades) if winning_trades else 0
    avg_loss = np.mean(losing_trades) if losing_trades else 0
    largest_win = max(winning_trades) if winning_trades else 0
    largest_loss = min(losing_trades) if losing_trades else 0
    avg_trade = np.mean(pnl_list) if pnl_list else 0

    # 5️⃣ Build response matching frontend expectations
    data = {
        "candles": candles,
        "signals": signals,  # Make sure your backtest engine returns signals
        "overview": {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "total_return": round(total_return, 2),
            "final_equity": round(final_balance, 2),
            "initial_capital": round(initial_balance, 2),
            "net_profit": round(net_profit, 2),
        },
        "performance": {
            "total_return_pct": round(total_return, 2),
            "annual_return": round(cagr, 2),
            "sharpe_ratio": safe_float(sharpe_ratio),
            "max_drawdown": round(max_drawdown * 100, 2),
            "volatility": round(std_return * 100, 2),
        },
        "risk_ratios": {
            "sharpe": safe_float(sharpe_ratio),
            "sortino": safe_float(sharpe_ratio),  # You might want to calculate proper Sortino ratio
            "calmar": safe_float(cagr / (max_drawdown * 100)) if max_drawdown > 0 else 0,
            "risk_reward_ratio": safe_float(avg_win / abs(avg_loss)) if avg_loss != 0 else float("inf"),
        },
        "trades": trades,
        "trade_analysis": {
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "avg_trade": round(avg_trade, 2),
            "profit_factor": safe_float(profit_factor),
            "longest_win_streak": longest_win_streak,
            "longest_loss_streak": longest_loss_streak,
            "avg_holding_time": avg_holding_time,
        },
        "equity_curve": equity_curve,
    }

    return response_message("Backtest successful", data)