from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class CustomerBase(BaseModel):
    name:str
    email_address:str
    customer_id:uuid.UUID|None=None
    Customer_id:uuid.UUID|None=None
    is_active:bool=True

class CustomerCreate(CustomerBase):
    pass 

class CustomerUpdate(CustomerBase):
    name:str|None=None
    email_address:str|None=None
    category_id:uuid.UUID|None=None
    Customer_id:uuid.UUID|None=None
    is_active:bool|None=None

class CustomerRead(CustomerBase):
    model_config=ConfigDict(from_attributes=True)

    customer_id:uuid.UUID
    created_at:datetime

