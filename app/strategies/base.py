# app/strategies/base.py
from typing import Dict

class Signal:
    def __init__(self, action: str):
        self.action = action  

class StrategyBase:
    def __init__(self, params: Dict):
        self.params = params

    def on_start(self, state):
        """Reset state before run"""
        pass

    def on_bar(self, candle: Dict) -> Signal:
        """Process one candle and return Signal"""
        raise NotImplementedError
