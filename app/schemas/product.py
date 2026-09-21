import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import StockReason
from app.schemas.common import Money, Percent


def _clean_barcode(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand_name: str = Field(min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    price: Money
    tax_rate: Percent = Decimal("0.00")
    category_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    is_active: bool = True

    _normalise_barcode = field_validator("barcode")(_clean_barcode)


class ProductCreate(ProductBase):
    # Opening balance only. Later changes go through stock adjustments so the ledger stays complete.
    stock_quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand_name: str | None = Field(default=None, min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    price: Money | None = None
    tax_rate: Percent | None = None
    category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    is_active: bool | None = None

    _normalise_barcode = field_validator("barcode")(_clean_barcode)


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    stock_quantity: int
    created_at: datetime


class StockAdjustmentCreate(BaseModel):
    quantity_change: int = Field(description="Positive adds stock, negative removes it")
    reason: StockReason = StockReason.ADJUSTMENT
    note: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("quantity_change")
    @classmethod
    def _non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_change must not be zero")
        return value

    @field_validator("reason")
    @classmethod
    def _manual_reasons_only(cls, value):
        allowed = {StockReason.RESTOCK, StockReason.ADJUSTMENT, StockReason.DAMAGE}
        if StockReason(value) not in allowed:
            raise ValueError("reason must be one of: restock, adjustment, damage")
        return value


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movement_id: uuid.UUID
    product_id: uuid.UUID
    sale_id: uuid.UUID | None
    quantity_change: int
    reason: str
    note: str | None
    created_by: uuid.UUID | None
    created_at: datetime