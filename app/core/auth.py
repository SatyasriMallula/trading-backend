# auth.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.core.config import Settings
from fastapi.security import  HTTPBearer,HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
SECRET_KEY = Settings().JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 256
REFRESH_TOKEN_EXPIRE_DAYS = 7
security=HTTPBearer()
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode ={"sub":data["sub"]}
    expire = datetime.utcnow() + (expires_delta or timedelta(  minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": data["sub"], "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials:HTTPAuthorizationCredentials=Depends(security)):
    try:
        token=credentials.credentials
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username:str=payload.get('sub')
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid authentication credentials", headers={"WWW-Authenticate": "Bearer"})
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token",headers={"WWW-Authenticate": "Bearer"})
