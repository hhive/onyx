from pydantic import BaseModel
from pydantic import EmailStr


class Sub2APIExchangeRequest(BaseModel):
    token: str


class Sub2APIExchangePayload(BaseModel):
    user_id: int
    email: EmailStr
    role: str
    api_key: str


class Sub2APIModel(BaseModel):
    id: str
    type: str | None = None
    display_name: str | None = None
