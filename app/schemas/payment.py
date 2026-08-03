from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class PaymentBase(BaseModel):
    name:str
    brand_name:str
    category:Decimal
    Payment_id:uuid.UUID|None=None
    stock_quantity:uuid.UUID
    is_active:bool=True

class PaymentCreate(PaymentBase):
    pass 

class PaymentUpdate(PaymentBase):
    name:str|None=None
    stock_quantity:uuid.UUID|None=None
    brand_name:str|None=None
    category:Decimal|None=None
    category_id:uuid.UUID|None=None
    is_active:bool|None=None

class PaymentRead(PaymentBase):
    model_config=ConfigDict(from_attributes=True)

    payment_id:uuid.UUID
    created_at:datetime

