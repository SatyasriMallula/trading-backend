from fastapi import FastAPI
import asyncio
from app.core.config import Settings
from app.routes import coindcx_socket_connection, paper_trading, strategies,backtest,live,auto,user,wallet 
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.services.trading_manager import trading_manager

app=FastAPI(title="Trading Backend",version="0.117.1")

# app.include_router(strategies.router,prefix="/strategies",tags=["Strategies"])
app.include_router(backtest.backtest_router)
app.include_router(paper_trading.paper_router)

# app.include_router(live.router,prefix="/live",tags=["Live Trading"])
# app.include_router(auto.router,prefix="/auto",tags=["Auto Trading"])
app.include_router(user.auth_router)
app.include_router(wallet.wallet_router)
app.include_router(coindcx_socket_connection.router)

@app.get('/')
async def root():
    return {"message": "Trading backend running 🚀"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start GENTLE cleanup task (24h threshold)
    cleanup_task = asyncio.create_task(trading_manager.cleanup_old_users())
    yield
    # On shutdown: gracefully stop all trading
    # This is still important for server restarts/deployments
    print("🔄 Shutting down all trading sessions...")
    for user_id in list(trading_manager.trading_tasks.keys()):
        await trading_manager.stop_trading(user_id)
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    print("✅ All trading sessions stopped")


settings=Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,      
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)
