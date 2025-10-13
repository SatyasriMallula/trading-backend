from passlib.context import CryptContext
pwd_context=CryptContext(schemes=["bcrypt"],deprecated=True)

def hash_password(password:str)->str:
    return pwd_context.hash(password)