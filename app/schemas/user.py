import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import UserRole
from app.schemas.common import LowerEmail, Username


class UserRegister(BaseModel):
    """Public self-registration. There is deliberately no `role` here: everyone
    who registers is a cashier. Elevated roles are granted by an admin."""

    username: Username
    email: LowerEmail
    password: str = Field(min_length=8, max_length=128)
    title: str = Field(default="Cashier", min_length=1, max_length=100)


class UserCreate(UserRegister):
    model_config = ConfigDict(use_enum_values=True)

    role: UserRole = UserRole.CASHIER
    is_active: bool = True


class UserUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    email: LowerEmail | None = None
    title: str | None = Field(default=None, min_length=1, max_length=100)
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    email: str
    title: str
    role: str
    is_active: bool
    created_at: datetime
