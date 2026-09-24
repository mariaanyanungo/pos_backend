import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    receipt_id: uuid.UUID
    receipt_number: str
    sale_id: uuid.UUID
    payment_id: uuid.UUID
    subtotal: Decimal
    discount: Decimal
    vat: Decimal
    total_amount: Decimal
    amount_tendered: Decimal | None
    change_due: Decimal
    prices_include_tax: bool
    is_active: bool
    created_at: datetime
