from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class SaleBase(BaseModel):
    
    amount:Decimal
    customer_id:uuid.UUID|None=None
    sale_id:uuid.UUID|None=None
    is_active:bool=True

class SaleCreate(SaleBase):
    pass 

class SaleUpdate(SaleBase):
    
    amount:Decimal|None=None
    customer_id:uuid.UUID|None=None
    sale_id:uuid.UUID|None=None
    is_active:bool|None=None

class SaleRead(SaleBase):
    model_config=ConfigDict(from_attributes=True)

    sale_id:uuid.UUID
    created_at:datetime

