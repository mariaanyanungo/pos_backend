from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid


class SupplierBase(BaseModel):
    name:str
    email:str
    phone_number:str
    supplier_address:str
    price:Decimal
    Supplier_id:uuid.UUID|None=None
    supplier_id:uuid.UUID|None=None
    is_active:bool=True

class SupplierCreate(SupplierBase):
    pass 

class SupplierUpdate(SupplierBase):
    email:str|None=None
    phone_number:str|None=None
    name:str|None=None
    supplier_address:str|None=None
    price:Decimal|None=None
    Supplier_id:uuid.UUID|None=None
    supplier_id:uuid.UUID|None=None
    is_active:bool|None=None

class SupplierRead(SupplierBase):
    model_config=ConfigDict(from_attributes=True)

    supplier_id:uuid.UUID
    created_at:datetime

