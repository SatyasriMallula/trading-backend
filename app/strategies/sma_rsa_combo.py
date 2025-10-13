# app/strategies/sma_rsi_combo.py
from .base import StrategyBase, Signal
from collections import deque
from typing import Dict, List

class SMA_RSI_Strategy(StrategyBase):
    def __init__(self, params: Dict):
        super().__init__(params)
        # SMA params
        self.short = params.short
        self.long = params.long
        self.prices: List[float] = []
        self.short_q = deque(maxlen=self.short)
        self.long_q = deque(maxlen=self.long)

        # RSI params
        self.rsi_period = params.period
        self.rsi_gains: List[float] = []
        self.rsi_losses: List[float] = []
        self.prev_close = None

    def on_start(self, state):
        self.prices.clear()
        self.short_q.clear()
        self.long_q.clear()
        self.rsi_gains.clear()
        self.rsi_losses.clear()
        self.prev_close = None

    def on_bar(self, candle: Dict) -> Signal:
        close = float(candle["close"])
        self.prices.append(close)
        self.short_q.append(close)
        self.long_q.append(close)

        # ---------- SMA calculation ----------
        if len(self.short_q) < self.short or len(self.long_q) < self.long:
            sma_signal = "HOLD"
        else:
            short_sma = sum(self.short_q) / self.short
            long_sma = sum(self.long_q) / self.long
            if short_sma > long_sma:
                sma_signal = "BUY"
            elif short_sma < long_sma:
                sma_signal = "SELL"
            else:
                sma_signal = "HOLD"

        # ---------- RSI calculation ----------
        if self.prev_close is None:
            self.prev_close = close
            rsi_signal = "HOLD"
        else:
            change = close - self.prev_close
            self.prev_close = close

            self.rsi_gains.append(max(change, 0))
            self.rsi_losses.append(abs(min(change, 0)))

            if len(self.rsi_gains) > self.rsi_period:
                self.rsi_gains.pop(0)
                self.rsi_losses.pop(0)

            if len(self.rsi_gains) < self.rsi_period:
                rsi_signal = "HOLD"
            else:
                avg_gain = sum(self.rsi_gains) / self.rsi_period
                avg_loss = sum(self.rsi_losses) / self.rsi_period
                rs = avg_gain / avg_loss if avg_loss != 0 else 100
                rsi = 100 - (100 / (1 + rs))
                if rsi > 70:
                    rsi_signal = "SELL"  # overbought
                elif rsi < 30:
                    rsi_signal = "BUY"   # oversold
                else:
                    rsi_signal = "HOLD"

        # ---------- Combine signals ----------
        # Only take BUY if both SMA trend and RSI agree
        if sma_signal == "BUY" and rsi_signal != "SELL":
            return Signal("BUY")
        elif sma_signal == "SELL" and rsi_signal != "BUY":
            return Signal("SELL")
        else:
            return Signal("HOLD")
