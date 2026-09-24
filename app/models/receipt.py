import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

_ZERO = Decimal("0.00")


class Receipt(Base):
    """Immutable proof of a completed sale (one per sale)."""

    __tablename__ = "receipts"

    receipt_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_number = Column(String(40), nullable=False, unique=True, index=True)
    sale_id = Column(
        Uuid(as_uuid=True), ForeignKey("sales.sale_id"), nullable=False, unique=True
    )
    payment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("payments.payment_id"),
        nullable=False,
        unique=True,
    )

    subtotal = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    vat = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    total_amount = Column(Numeric(12, 2), nullable=False)
    amount_tendered = Column(Numeric(12, 2), nullable=True)
    change_due = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    prices_include_tax = Column(Boolean, nullable=False, default=False)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sale = relationship("Sale", back_populates="receipt")
    payment = relationship("Payment", back_populates="receipt")
