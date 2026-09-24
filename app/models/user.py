import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Uuid
from sqlalchemy.sql import func

from app.core.enums import UserRole
from database import Base


class User(Base):
    """A staff member who operates the POS (not a shopper - see Customer)."""

    __tablename__ = "users"

    user_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    title = Column(String(100), nullable=False, default="Cashier")
    role = Column(
        String(20), nullable=False, default=UserRole.CASHIER.value, index=True
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
