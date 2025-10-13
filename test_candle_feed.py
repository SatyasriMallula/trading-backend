import asyncio
from app.coindxc_sockets.candlesticks import CandleStick

async def test_candle_feed():
    """Test the candle feed with different intervals"""
    
    # Test different pairs and intervals
    test_configs = [
        {"pair": "B-BTC_USDT", "interval": "1m"},
        {"pair": "B-ETH_USDT", "interval": "5m"},
        {"pair": "B-BNB_USDT", "interval": "15m"}
    ]
    
    async def candle_callback(candle_data):
        print(f"\n🎯 CANDLE RECEIVED:")
        print(f"Symbol: {candle_data.get('symbol')}")
        print(f"Interval: {candle_data.get('interval')}")
        print(f"Open: {candle_data.get('open')}")
        print(f"High: {candle_data.get('high')}")
        print(f"Low: {candle_data.get('low')}")
        print(f"Close: {candle_data.get('close')}")
        print(f"Volume: {candle_data.get('volume')}")
        print(f"Is Closed: {candle_data.get('is_closed')}")
        print(f"Time: {candle_data.get('time')}")
        print("-" * 50)
    
    feeds = []
    
    for config in test_configs:
        feed = CandleStick(
            pair=config["pair"],
        )
        feed.register_callback(candle_callback)
        feeds.append(feed)
        print(f"📡 Started {config['pair']} {config['interval']} candle feed")
    
    # Start all feeds
    tasks = [asyncio.create_task(feed.start()) for feed in feeds]
    
    try:
        print("⏳ Listening for candle updates (run for 2 minutes)...")
        await asyncio.sleep(120)  # Run for 2 minutes
    except KeyboardInterrupt:
        print("🛑 Stopped by user")
    finally:
        # Cleanup
        for task in tasks:
            task.cancel()
        print("🧹 Cleanup completed")

if __name__ == "__main__":
    asyncio.run(test_candle_feed())