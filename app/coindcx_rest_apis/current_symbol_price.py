import requests

def get_current_price(symbol):
    response = requests.get("https://api.coindcx.com/exchange/ticker")  # full list
    data = response.json()  # list of dicts
    
    # Loop through the list to find the matching symbol
    for market_data in data:
        if market_data.get('market') == symbol:
            # Some markets may use 'last_price', some may use 'ask' if no 'last_price'
            price = float(market_data.get('last_price') or market_data.get('ask'))
            print(f"Current price of {symbol}: {price}")
            return price
    
    raise ValueError(f"No data found for symbol {symbol}")
