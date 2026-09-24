import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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

from app.core.enums import SaleStatus
from database import Base

_ZERO = Decimal("0.00")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_sales_total_non_negative"),
    )

    sale_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("customers.customer_id"),
        nullable=True,
        index=True,
    )
    cashier_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    status = Column(
        String(20), nullable=False, default=SaleStatus.OPEN.value, index=True
    )
    prices_include_tax = Column(Boolean, nullable=False, default=False)

    subtotal = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    discount_total = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    tax_total = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    total_amount = Column(Numeric(12, 2), nullable=False, default=_ZERO)

    void_reason = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    voided_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="sales")
    items = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="SaleItem.created_at",
    )
    payments = relationship("Payment", back_populates="sale")
    receipt = relationship("Receipt", back_populates="sale", uselist=False)
