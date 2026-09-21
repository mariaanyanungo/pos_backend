import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.enums import PaymentStatus
from database import Base

_ZERO = Decimal("0.00")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("refunded_amount >= 0 AND refunded_amount <= amount", name="ck_payments_refund_range"),
    )

    payment_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(Uuid(as_uuid=True), ForeignKey("sales.sale_id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)               # amount applied to the sale
    amount_tendered = Column(Numeric(12, 2), nullable=True)       # cash handed over
    change_due = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    payment_method = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=PaymentStatus.PENDING.value, index=True)

    
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    request_fingerprint = Column(String(64), nullable=False)

    gateway_reference = Column(String(100), nullable=True)
    failure_reason = Column(String(500), nullable=True)
    refunded_amount = Column(Numeric(12, 2), nullable=False, default=_ZERO)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=True)

    sale = relationship("Sale", back_populates="payments")
    receipt = relationship("Receipt", back_populates="payment", uselist=False)