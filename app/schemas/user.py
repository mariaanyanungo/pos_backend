from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class UserBase(BaseModel):
    username:str
    title:str
    customer_id:uuid.UUID|None=None
    user_id:uuid.UUID|None=None
    is_active:bool=True

class UserCreate(UserBase):
    pass 

class UserUpdate(UserBase):
    username:str|None=None
    email:str| None=None
    password:str|None|None
    is_active:bool|None=None

class UserRead(UserBase):
    model_config=ConfigDict(from_attributes=True)
    user_id:uuid.UUID
    created_at:datetime
    is_active:bool

