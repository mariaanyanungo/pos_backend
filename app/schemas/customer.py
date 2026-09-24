import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LowerEmail


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: LowerEmail | None = None
    phone: str | None = Field(default=None, max_length=50)
    is_active: bool = True


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: LowerEmail | None = None
    phone: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    customer_id: uuid.UUID
    created_at: datetime
