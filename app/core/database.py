from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.DATABASE_NAME]

db_paper=client["paper_trading"]
db_user=client["users"]

user=db_user["user"]
wallets=db_paper["wallets"]
trades=db_paper["trades"]
positions=db_paper["positions"]