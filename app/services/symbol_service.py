import aiohttp
class SymbolService:
    def __init__(self):
        self.symbol_cache = {}
    
    async def get_pair_for_symbol(self, symbol: str) -> str:
        """Get pair from symbol using CoinDCX API"""
        if symbol in self.symbol_cache:
            return self.symbol_cache[symbol]
        
        try:
            async with aiohttp.ClientSession() as session:
                # CoinDCX markets API
                url = "https://api.coindcx.com/exchange/v1/markets_details"
                async with session.get(url) as response:
                    markets = await response.json()
                    
                    # Find the pair for this symbol
                    for market in markets:
                        if market.get('symbol') == symbol and market.get('status') == 'active':
                            pair = market['pair']
                            self.symbol_cache[symbol] = pair
                            return pair
                    
                    raise ValueError(f"Symbol {symbol} not found in active markets")
                    
        except Exception as e:
            print(f"Error fetching pair for {symbol}: {e}")
            raise