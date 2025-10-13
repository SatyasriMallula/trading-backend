# app/strategies/rsi.py
from .base import StrategyBase, Signal
from typing import Dict, List

class RSI_Strategy(StrategyBase):
    def __init__(self, params: Dict):
        super().__init__(params)
        self.period = params.period
        self.gains: List[float] = []
        self.losses: List[float] = []
        self.prev_close = None

    def on_start(self, state):
        self.gains.clear()
        self.losses.clear()
        self.prev_close = None

    def on_bar(self, candle: Dict) -> Signal:
        close = float(candle["close"])
        if self.prev_close is None:
            self.prev_close = close
            return Signal("HOLD")

        change = close - self.prev_close
        self.prev_close = close

        self.gains.append(max(change, 0))
        self.losses.append(abs(min(change, 0)))

        if len(self.gains) > self.period:
            self.gains.pop(0)
            self.losses.pop(0)

        if len(self.gains) < self.period:
            return Signal("HOLD")

        avg_gain = sum(self.gains) / self.period
        avg_loss = sum(self.losses) / self.period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        if rsi > 70:
            return Signal("SELL")
        elif rsi < 30:
            return Signal("BUY")
        return Signal("HOLD")
