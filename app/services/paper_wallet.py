from datetime import datetime
from app.core.database import wallets, positions, trades
from app.utils.time_date_format import format_date

class PaperWallet:
    def __init__(self, user_id: str, initial_cash: float = 1000.0):
        self.user_id = user_id
        self.total_balance = initial_cash      # never changes unless deposit/withdraw
        self.available_balance = initial_cash  # changes with trades
        self.positions = {}                    # symbol -> qty

    # -------------------------
    # BUY
    # -------------------------
    async def buy(self, symbol: str, price: float, trade_qty: float, fee: float = 0.0):
        cost = price * trade_qty + fee
        if self.available_balance < cost:
            return False

        self.available_balance -= cost
        self.positions[symbol] = self.positions.get(symbol, 0) + trade_qty

        # Log trade
        trade_doc = {
            "user_id": self.user_id,
            "symbol": symbol,
            "side": "BUY",
            "price": price,
            "qty": trade_qty,
            "fee": fee,
            "timestamp": format_date(datetime.now()),
            "mode": "paper"
        }
        await trades.insert_one(trade_doc)

        # Update position
        await positions.update_one(
            {"user_id": self.user_id, "symbol": symbol},
            {
                "$set": {
                    "qty": trade_qty,
                    "entry_price": price,
                    "current_price": price,
                    "side": "BUY",
                    "is_closed": False,
                    "realized_pnl": 0,
                    "last_updated": format_date(datetime.now())
                }
            },
            upsert=True
        )

        # Update wallet balances
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

    # -------------------------
    # SELL
    # -------------------------
    async def sell(self, symbol: str, price: float, trade_qty: float, fee: float = 0.0):
        current_qty = self.positions.get(symbol, 0)
        if current_qty < trade_qty:
            return False

        # Calculate proceeds & realized PnL
        proceeds = price * trade_qty - fee
        entry_price = await self._get_entry_price(symbol)
        realized_pnl = (price - entry_price) * trade_qty

        self.available_balance += proceeds
        self.positions[symbol] -= trade_qty

        # Update position in DB
        await positions.update_one(
            {"user_id": self.user_id, "symbol": symbol},
            {
                "$set": {
                    "qty":trade_qty,
                    "current_price": price,
                    "is_closed": self.positions[symbol] <= 0,
                    "realized_pnl": realized_pnl,
                    "last_updated": format_date(datetime.now())
                }
            }
        )

        # Log trade
        trade_doc = {
            "user_id": self.user_id,
            "symbol": symbol,
            "side": "SELL",
            "price": price,
            "qty": trade_qty,
            "fee": fee,
            "realized_pnl": realized_pnl,
            "timestamp": format_date(datetime.now()),
            "mode": "paper"
        }
        await trades.insert_one(trade_doc)

        # Update wallet balances
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

    # -------------------------
    # Get entry price from DB
    # -------------------------
    async def _get_entry_price(self, symbol: str) -> float:
        pos = await positions.find_one({"user_id": self.user_id, "symbol": symbol})
        if pos:
            return pos.get("entry_price", 0.0)
        return 0.0

    # -------------------------
    # Calculate portfolio value
    # -------------------------
    async def portfolio_value(self, current_prices: dict) -> float:
        value = self.available_balance
        for sym, qty in self.positions.items():
            if qty > 0:
                entry_price = await self._get_entry_price(sym)
                current_price = current_prices.get(sym, entry_price)
                value += qty * current_price
        return value

    # -------------------------
    # Deposit / Withdraw
    # -------------------------
    async def deposit(self, amount: float):
        self.total_balance += amount
        self.available_balance += amount
        await wallets.update_one(
            {"user_id": self.user_id},
            {"$set": {
                "total_balance": self.total_balance,
                "available_balance": self.available_balance,
                "updated_at": format_date(datetime.now())
            }},
            upsert=True
        )

    async def withdraw(self, amount: float) -> bool:
        if self.available_balance >= amount:
            self.total_balance -= amount
            self.available_balance -= amount
            await wallets.update_one(
                {"user_id": self.user_id},
                {"$set": {
                    "total_balance": self.total_balance,
                    "available_balance": self.available_balance,
                    "updated_at": format_date(datetime.now())
                }},
                upsert=True
            )
            return True
        return False
