from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class ProductBase(BaseModel):
    name:str
    brand_name:str
    price:Decimal
    category_id:uuid.UUID|None=None
    supplier_id:uuid.UUID|None=None
    is_active:bool=True

class ProductCreate(ProductBase):
    pass 

class ProductUpdate(ProductBase):
    name:str|None=None
    brand_name:str|None=None
    price:Decimal|None=None
    category_id:uuid.UUID|None=None
    supplier_id:uuid.UUID|None=None
    is_active:bool|None=None

class ProductRead(BaseModel):
    
    model_config=ConfigDict(from_attributes=True)

    product_id:uuid.UUID
    created_at:datetime

