from pydantic import BaseModel,Field
import uuid
from uuid import UUID
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    id:UUID=Field(default_factory=uuid.uuid4)
    username:str
    access_token: str
    refresh_token: str
    