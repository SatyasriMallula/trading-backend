import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    # MongoDB settings
    
    # MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_URL: str = ("mongodb://localhost:27017")

    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "tradingbot")
    
    COINDCX_WEBSOCKET_URL:str= 'wss://stream.coindcx.com'

    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3000

    # # Stripe settings
    # STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "sk_test_51R4hFWEi7L0cpUmSD625gUIerHKn2bUgsydMVdFM9AybFylVCnKiRj2OnqiRBwGWacir3fno3nHwzNOWFykKWY4J00amGLjWKO")
    # STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_51R4hFWEi7L0cpUmS4hrokKeqW7IlLnXCmaTHm2mOOQIauzNgEU07BNPIlthXh7UBa009j0wkAFs")
    # STRIPE_WEBHOOK_SECRET_KEY: str = os.getenv("STRIPE_WEBHOOK_SECRET_KEY", "whsec_8kFiir6NV5jqO9Y196h95t7ICRrp5eSr")


    # BREXA_STRIPE_SECRET_KEY: str
    # BREXA_STRIPE_PUBLISHABLE_KEY: str
    # BREXA_STRIPE_WEBHOOK_SECRET_KEY: str

   
    # CORS settings
    CORS_ORIGINS: list =["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
