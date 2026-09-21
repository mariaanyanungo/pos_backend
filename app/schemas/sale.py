import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import PaymentMethod
from app.schemas.payment import PaymentRead
from app.schemas.receipt import ReceiptRead
from app.schemas.sale_item import SaleItemRead


class SaleCreate(BaseModel):
    customer_id: uuid.UUID | None = None


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sale_id: uuid.UUID
    customer_id: uuid.UUID | None
    cashier_id: uuid.UUID
    status: str
    prices_include_tax: bool
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total_amount: Decimal
    void_reason: str | None
    created_at: datetime
    completed_at: datetime | None
    voided_at: datetime | None
    items: list[SaleItemRead] = []


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    payment_method: PaymentMethod
    amount_tendered: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)] | None = None

    @model_validator(mode="after")
    def _cash_requires_tender(self):
        if self.payment_method == PaymentMethod.CASH and self.amount_tendered is None:
            raise ValueError("amount_tendered is required for cash payments")
        return self


class CheckoutResponse(BaseModel):
    sale: SaleRead
    payment: PaymentRead
    receipt: ReceiptRead | None = None


class VoidRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RefundLine(BaseModel):
    sale_item_id: uuid.UUID
    quantity: int = Field(ge=1)


class RefundRequest(BaseModel):
    items: list[RefundLine] = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=500)


class RefundResponse(BaseModel):
    sale: SaleRead
    payment: PaymentRead
    refunded_amount: Decimal