# app/strategies/__init__.py
from .sma_cross import SMA_Crossover
from .rsi import RSI_Strategy
from .sma_rsa_combo import SMA_RSI_Strategy
STRATEGY_REGISTRY = {
    "sma_crossover": SMA_Crossover,
    "rsi": RSI_Strategy,
    "sma_rsi":SMA_RSI_Strategy
}
