from pydantic import BaseModel, EmailStr
from typing import Optional

class StrategyParams(BaseModel):
    short:Optional[int]=None
    long:Optional[int]=None
    period:Optional[int]=None

class CandleParams(BaseModel):
    interval:str
    limit:int=500
    pair:str
    startTime:Optional[str]
    endTime:Optional[str]

class BacktestRequest(BaseModel):
    strategy:str
    timeframe:Optional[str]
    initial_capital:float
    fee_rate:float=0.001
    position_size_pct:float=1.0
    params:StrategyParams
    candle_params:CandleParams

class BacktestResult(BaseModel):
    win_rate:float
    profit_factor:float
    max_drawdown:float
    net_profit:float

class Order(BaseModel):
    id:str
    type:str
    symbol:str
    qty:float
    price:float
    status:str

class User(BaseModel):
    user_id:str
    username:str
    email:EmailStr
    hashed_password:str
    is_active:bool=True
    is_superuser:bool=False

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    message: str


    