import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID
    sale_id: uuid.UUID
    amount: Decimal
    amount_tendered: Decimal | None
    change_due: Decimal
    payment_method: str
    status: str
    idempotency_key: str
    gateway_reference: str | None
    failure_reason: str | None
    refunded_amount: Decimal
    created_at: datetime
    captured_at: datetime | None
