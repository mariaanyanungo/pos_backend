from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class Sale_itemBase(BaseModel):
    barcode:str
    unit_price:Decimal
    sale_item_id:uuid.UUID|None=None
    sale_id:uuid.UUID|None=None
    is_active:bool=True

class Sale_itemCreate(Sale_itemBase):
    pass 

class Sale_itemUpdate(Sale_itemBase):
    barcode:str|None=None
    unit_price:Decimal|None=None
    sale_item_id:uuid.UUID|None=None
    sale_id:uuid.UUID|None=None
    is_active:bool|None=None

class Sale_itemRead(Sale_itemBase):
    model_config=ConfigDict(from_attributes=True)

    sale_item_id:uuid.UUID
    created_at:datetime

