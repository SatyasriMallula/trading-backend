from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from app.utils.time_date_format import format_date, format_time
from app.schemas.backtest import StrategyParams

class DepositRequest(BaseModel):
    user_id: str
    amount: float

class WithdrawRequest(BaseModel):
    user_id: str
    amount: float

class Trade(BaseModel):
    user_id: str
    symbol: str
    side: str   # "BUY" or "SELL"
    price: float
    qty: float
    fee: Optional[float] = 0.0
    timestamp: str = None
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return format_time(datetime.now())

class Position(BaseModel):
    user_id: str
    symbol: str
    qty: float
    entry_price: Optional[float] = 0.0
    current_price: Optional[float] = 0.0
    side: Optional[str] = "BUY"  # "BUY" or "SELL"

class Wallet(BaseModel):
    user_id: str
    total_balance: float  # Changed from cash
    available_balance: float  # New field
    currency: Optional[str] = "USDT"
    created_at: str = None  # Change to string type
    updated_at: Optional[str] = None
    
    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return format_date(datetime.now())
    
    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return format_date(datetime.now())

class PaperTrading(BaseModel):
    user_id: str
    symbol: str
    timeframe: str
    qty: float
    strategy_name: str
    strategy_params: Optional[StrategyParams] = None

# Optional: Response models for better API responses
class WalletResponse(BaseModel):
    user_id: str
    total_balance: float
    available_balance: float
    positions_value: float  # total_balance - available_balance
    currency: str
    created_at: str  # Change to string type
    updated_at: str  # Change to string type

class TradingStatusResponse(BaseModel):
    user_id: str
    is_trading: bool
    symbol: Optional[str] = None
    strategy: Optional[str] = None
    started_at: Optional[str] = None  # Change to string type

class CreateWalletRequest(BaseModel):
    user_id: str
    initial_balance: float = 1000.0
    currency: str = "USDT"