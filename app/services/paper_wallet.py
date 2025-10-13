from datetime import datetime, timezone
from app.core.database import wallets, positions, trades
from app.utils.time_date_format import format_date
class PaperWallet:
    def __init__(self, user_id: str, initial_cash: float = 1000.0):
        self.user_id = user_id
        self.total_balance = initial_cash  # Never changes unless deposit/withdraw
        self.available_balance = initial_cash  # Changes with trades
        self.positions = {}  # symbol -> qty

    async def buy(self, symbol: str, price: float, qty: float, fee: float = 0.0):
        print("received args", symbol, price, qty)
        cost = price * qty + fee
        print(f"Available balance: {self.available_balance}, Cost: {cost}")
        
        if self.available_balance >= cost:
            print("yes", self.available_balance)
            # Only reduce available balance, total balance remains same
            self.available_balance -= cost
            self.positions[symbol] = self.positions.get(symbol, 0) + qty

            # Log to DB
            trade_doc = {
                "user_id": self.user_id,
                "symbol": symbol,
                "side": "BUY",
                "price": price,
                "qty": qty,
                "fee": fee,
                "timestamp":format_date(datetime.now()),
                "mode": "paper"
            }
            print(trade_doc)
            
            try:
                result = await trades.insert_one(trade_doc)
                print("✅ Trade inserted with id:", result.inserted_id)
            except Exception as e:
                print("❌ Trade insert failed:", e)

            # Update wallet with both balances
            try:
                await wallets.update_one(
                    {"user_id": self.user_id}, 
                    {
                        "$set": {
                            "total_balance": self.total_balance,
                            "available_balance": self.available_balance,
                            "updated_at": format_date(datetime.now())
                        }
                    }, 
                    upsert=True
                )
                
                # Update position
                await positions.update_one(
                    {"user_id": self.user_id, "symbol": symbol},
                    {
                        "$set": {
                            "qty": self.positions[symbol],
                            "entry_price": price,
                            "current_price": price,
                            "side": "BUY",
                            "last_updated": format_date(datetime.now())
                        }
                    }, 
                    upsert=True
                )
                print("✅ Wallet and position updated successfully")
            except Exception as e:
                print("❌ Database update failed:", e)
                
            return True
        return False

    async def sell(self, symbol: str, price: float, qty: float, fee: float = 0.0):
        current_position = self.positions.get(symbol, 0)
        if current_position >= qty:
            # Calculate proceeds after fee
            proceeds = price * qty - fee
            
            # Only increase available balance, total balance remains same
            self.available_balance += proceeds
            self.positions[symbol] -= qty

            # If position is completely closed, remove it
            if self.positions[symbol] <= 0:
                self.positions.pop(symbol, None)

            # Log to DB
            trade_doc = {
                "user_id": self.user_id,
                "symbol": symbol,
                "side": "SELL",
                "price": price,
                "qty": qty,
                "fee": fee,
                "timestamp":format_date(datetime.now()),
                "mode": "paper"
            }
            print(trade_doc)
            
            try:
                result = await trades.insert_one(trade_doc)
                print("✅ Trade inserted with id:", result.inserted_id)
            except Exception as e:
                print("❌ Trade insert failed:", e)

            # Update wallet and position in database
            try:
                # Update wallet with both balances
                await wallets.update_one(
                    {"user_id": self.user_id}, 
                    {
                        "$set": {
                            "total_balance": self.total_balance,
                            "available_balance": self.available_balance,
                            "updated_at":format_date(datetime.now())
                        }
                    }, 
                    upsert=True
                )
                
                if symbol in self.positions:
                    # Update remaining position
                    await positions.update_one(
                        {"user_id": self.user_id, "symbol": symbol},
                        {
                            "$set": {
                                "qty": self.positions[symbol],
                                "current_price": price,
                                "last_updated": format_date(datetime.now())
                            }
                        }
                    )
                else:
                    # Remove position if completely sold
                    await positions.delete_one({"user_id": self.user_id, "symbol": symbol})
                    
                print("✅ Wallet and position updated successfully")
            except Exception as e:
                print("❌ Database update failed:", e)
                
            return True
        return False

    def portfolio_value(self, current_prices: dict):
        """Calculate total portfolio value including positions"""
        # Portfolio value = available balance + value of all positions
        position_value = 0
        for sym, qty in self.positions.items():
            position_value += qty * current_prices.get(sym, 0)
        
        return self.available_balance + position_value

    async def deposit(self, amount: float):
        """Add funds to both total and available balance"""
        self.total_balance += amount
        self.available_balance += amount
        
        await wallets.update_one(
            {"user_id": self.user_id}, 
            {
                "$set": {
                    "total_balance": self.total_balance,
                    "available_balance": self.available_balance,
                    "updated_at": format_date(datetime.now())
                }
            }, 
            upsert=True
        )

    async def withdraw(self, amount: float):
        """Withdraw funds if sufficient available balance"""
        if self.available_balance >= amount:
            self.total_balance -= amount
            self.available_balance -= amount
            
            await wallets.update_one(
                {"user_id": self.user_id}, 
                {
                    "$set": {
                        "total_balance": self.total_balance,
                        "available_balance": self.available_balance,
                        "updated_at": format_date(datetime.now())
                    }
                }, 
                upsert=True
            )
            return True
        return False