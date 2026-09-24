import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Money, Percent


class SaleItemCreate(BaseModel):
    product_id: uuid.UUID | None = None
    barcode: str | None = Field(default=None, min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=100000)
    discount_amount: Money | None = None
    discount_percent: Percent | None = None

    @model_validator(mode="after")
    def _validate(self):
        if (self.product_id is None) == (self.barcode is None):
            raise ValueError("Provide exactly one of product_id or barcode")
        if self.discount_amount is not None and self.discount_percent is not None:
            raise ValueError(
                "Provide either discount_amount or discount_percent, not both"
            )
        return self


class SaleItemUpdate(BaseModel):
    """PATCH semantics: only fields that are sent are changed. Sending both
    discount fields as null (or one of them as null) clears the discount."""

    quantity: int | None = Field(default=None, ge=1, le=100000)
    discount_amount: Money | None = None
    discount_percent: Percent | None = None

    @model_validator(mode="after")
    def _validate(self):
        if self.discount_amount is not None and self.discount_percent is not None:
            raise ValueError(
                "Provide either discount_amount or discount_percent, not both"
            )
        return self


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sale_item_id: uuid.UUID
    sale_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    barcode: str | None
    unit_price: Decimal
    tax_rate: Decimal
    quantity: int
    discount_percent: Decimal | None
    discount_amount: Decimal
    line_subtotal: Decimal
    tax_amount: Decimal
    line_total: Decimal
    returned_quantity: int
    refunded_total: Decimal
    created_at: datetime
