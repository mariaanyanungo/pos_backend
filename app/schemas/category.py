from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid
class CategoryBase(BaseModel):
    name:str
    category_id:uuid.UUID|None=None
    Category_id:uuid.UUID|None=None
    is_active:bool=True

class CategoryCreate(CategoryBase):
    pass 

class CategoryUpdate(CategoryBase):
    name:str|None=None
    category_id:uuid.UUID|None=None
    Category_id:uuid.UUID|None=None
    is_active:bool|None=None

class CategoryRead(CategoryBase):
    model_config=ConfigDict(from_attributes=True)

    category_id:uuid.UUID
    created_at:datetime

