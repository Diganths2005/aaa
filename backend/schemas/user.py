from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str
