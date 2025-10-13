import requests, time
from typing import List, Dict
COINDCX_URL = "https://public.coindcx.com/market_data/candles/"

def fetch_coindcx_candles(pair: str, interval: str, limit:int=500, startTime: int=None, endTime: int=None) -> List[Dict]:
    params = {"pair": pair, "interval": interval, "limit": str(limit)}
    if startTime: params["startTime"] = str(startTime)
    if endTime: params["endTime"] = str(endTime)
    r = requests.get(COINDCX_URL, params=params, timeout=10)
    r.raise_for_status()
    raw = r.json()
    # Convert each item to {time, open, high, low, close, volume}
    candles = []
    for d in raw:
        candles.append({
            "time": int(d.get("time", d.get("open_time", 0))),
            "open": float(d["open"]),
            "high": float(d["high"]),
            "low": float(d["low"]),
            "close": float(d["close"]),
            "volume": float(d["volume"]),
        })
    return candles
