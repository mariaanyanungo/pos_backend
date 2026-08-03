from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
import uuid

class ReceiptBase(BaseModel):
    
    vat:Decimal
    change:Decimal
    discount:Decimal
    payment_id:uuid.UUID|None=None
    receipt_id:uuid.UUID|None=None
    is_active:bool=True

class ReceiptCreate(ReceiptBase):
    pass 

class ReceiptUpdate(ReceiptBase):
    
    vat:Decimal|None=None
    change:Decimal|None=None
    discount:Decimal|None=None
    payment_id:uuid.UUID|None=None
    receipt_id:uuid.UUID|None=None
    is_active:bool|None=None

class ReceiptRead(ReceiptBase):
    model_config=ConfigDict(from_attributes=True)

    receipt_id:uuid.UUID
    created_at:datetime

