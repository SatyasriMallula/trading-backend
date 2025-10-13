from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from app.core.config import settings
# from app.core.database import Database

security = HTTPBearer()


async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    
    try:
        payload = jwt.decode(token.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        print("jhgjkggfjggfh",payload)
        user_id = payload.get("username")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: no user_id")
        # Check user existence and is_active
        # db = Database.get_db()
        # user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user_id:
        # or not user.get("is_active", True):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
