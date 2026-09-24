import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LowerEmail


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: LowerEmail
    phone: str = Field(min_length=3, max_length=50)
    address: str = Field(min_length=1, max_length=500)
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: LowerEmail | None = None
    phone: str | None = Field(default=None, min_length=3, max_length=50)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    is_active: bool | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    supplier_id: uuid.UUID
    created_at: datetime
