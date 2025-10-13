# app/strategies/sma_cross.py
from .base import StrategyBase, Signal
from collections import deque
from typing import Dict, List
from app.schemas.backtest import StrategyParams


class SMA_Crossover(StrategyBase):
    def __init__(self, params: StrategyParams):
        super().__init__(params)
        self.short = params.short
        self.long = params.long
        self.prices = []
        self.short_q = deque(maxlen=self.short)
        self.long_q = deque(maxlen=self.long)
        self.prev_short_sma = None
        self.prev_long_sma = None
        self.position = 0  # 0 = no position, 1 = long

    def on_start(self, state):
        self.prices.clear()
        self.short_q.clear()
        self.long_q.clear()
        self.prev_short_sma = None
        self.prev_long_sma = None
        self.position = 0

    def on_bar(self, candle: Dict) -> Signal:
        price = float(candle["close"])
        self.prices.append(price)
        self.short_q.append(price)
        self.long_q.append(price)

        if len(self.short_q) < self.short or len(self.long_q) < self.long:
            return 

        short_sma = sum(self.short_q) / self.short
        long_sma = sum(self.long_q) / self.long
        signal = Signal("HOLD")

        # CROSSOVER DETECTION
        if self.prev_short_sma is not None and self.prev_long_sma is not None:
            # BUY only if no open position
            if self.position == 0 and short_sma > long_sma and self.prev_short_sma <= self.prev_long_sma:
                signal = Signal("BUY")
                self.position = 1
            # SELL only if we currently hold a position
            elif self.position == 1 and short_sma < long_sma and self.prev_short_sma >= self.prev_long_sma:
                signal = Signal("SELL")
                self.position = 0

        # update previous SMA values
        self.prev_short_sma = short_sma
        self.prev_long_sma = long_sma

        return signal
