from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class UserBase(BaseModel):
    title:str
    usertitle:str
    customer_id:uuid.UUID|None=None
    user_id:uuid.UUID|None=None
    is_active:bool=True

class UserCreate(UserBase):
    pass 

class UserUpdate(UserBase):
    name:str|None=None
    username:str|None=None
    customer_id:uuid.UUID|None=None
    user_id:uuid.UUID|None=None
    is_active:bool|None=None

class UserRead(UserBase):
    model_config=ConfigDict(from_attributes=True)
    user_id:uuid.UUID
    created_at:datetime

