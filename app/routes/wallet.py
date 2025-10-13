from fastapi import APIRouter,Depends
from  app.core.database import wallets, db_paper
from app.schemas.paper_trade import CreateWalletRequest
from app.services.paper_wallet import PaperWallet
from app.utils.response_message import response_message
from app.utils.serialize_doc import serialize_doc
from app.core.auth import get_current_user
from app.schemas.paper_trade import DepositRequest, WithdrawRequest
import datetime
from app.utils.time_date_format import format_date
wallet_router=APIRouter(prefix="/api/wallet",tags=["Wallet"])


@wallet_router.get("/{user_id}")
async def get_wallet(user_id,current_user:str=Depends(get_current_user)):
    response=await wallets.find_one({"user_id":user_id})
    return response_message(message="Wallet fetched successfully",data=serialize_doc(response))


@wallet_router.post('/')
async def create_wallet(request: CreateWalletRequest, current_user: str = Depends(get_current_user)):
    """Create a new paper wallet using PaperWallet class"""
    try:
        # Check if wallet already exists
        existing = await wallets.find_one({"user_id": request.user_id})
        if existing:
            return response_message(code=400, message="Wallet already exists")
        
        # ✅ Create PaperWallet instance - this handles all the logic
        wallet = PaperWallet(
            user_id=request.user_id, 
            initial_cash=request.initial_balance
        )
        
        # ✅ Let the PaperWallet initialize itself in database
        # This ensures consistent state between memory and database
        await wallets.insert_one({
            "user_id": wallet.user_id,
            "total_balance": wallet.total_balance,
            "available_balance": wallet.available_balance,
            "currency": request.currency,
            "created_at": format_date(datetime),
            "updated_at": format_date(datetime)
        })
        
        # ✅ You might want to store the PaperWallet instance in your trading manager
        # trading_manager.initialize_wallet(wallet)  # If you have such a system
        
        return response_message(
            code=201, 
            message=f"Wallet created with ${request.initial_balance} initial balance",
            data={
                "user_id": wallet.user_id,
                "total_balance": wallet.total_balance,
                "available_balance": wallet.available_balance
            }
        )
        
    except Exception as e:
        return response_message(
            code=500, 
            message=f"Failed to create wallet: {str(e)}", 
        )

# app/routes/paper_trading.py

@wallet_router.post("/deposit")
async def deposit_funds(request: DepositRequest, current_user: str = Depends(get_current_user)):
    """Add funds to paper wallet"""
    try:
        # Get user's wallet
        wallet_doc = await wallets.find_one({"user_id": request.user_id})
        if not wallet_doc:
            return {"status": "error", "msg": "Wallet not found"}
        
        # Update wallet in database
        new_total = wallet_doc.get("total_balance", 0) + request.amount
        new_available = wallet_doc.get("available_balance", 0) + request.amount
        
        await wallets.update_one(
            {"user_id": request.user_id},
            {
                "$set": {
                    "total_balance": new_total,
                    "available_balance": new_available,
                    "updated_at": format_date(datetime)
                }
            }
        )
        
        return response_message(
            message=f"Deposited ${request.amount} successfully",
            data={
                "new_total_balance": new_total,
                "new_available_balance": new_available
            }
        )
        
    except Exception as e:
        return response_message(message=f"Deposit failed: {str(e)}", success=False)

@wallet_router.post("/withdraw")
async def withdraw_funds(request: WithdrawRequest, current_user: str = Depends(get_current_user)):
    """Withdraw funds from paper wallet"""
    try:
        wallet_doc = await wallets.find_one({"user_id": request.user_id})
        if not wallet_doc:
            return {"status": "error", "msg": "Wallet not found"}
        
        current_available = wallet_doc.get("available_balance", 0)
        
        if current_available < request.amount:
            return response_message(
                message="Insufficient available balance for withdrawal",
               
            )
        
        # Update wallet
        new_total = wallet_doc.get("total_balance", 0) - request.amount
        new_available = current_available - request.amount
        
        await wallets.update_one(
            {"user_id": request.user_id},
            {
                "$set": {
                    "total_balance": new_total,
                    "available_balance": new_available,
                    "updated_at": format_date(datetime)
                }
            }
        )
        
        return response_message(
            message=f"Withdrew ${request.amount} successfully",
            data={
                "new_total_balance": new_total,
                "new_available_balance": new_available
            }
        )
        
    except Exception as e:
        return response_message(message=f"Withdrawal failed: {str(e)}")