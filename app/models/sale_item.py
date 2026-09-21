

import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

_ZERO = Decimal("0.00")


class SaleItem(Base):
    """One cart line. Name, barcode, price and tax rate are snapshotted so that
    later catalogue edits never rewrite history."""

    __tablename__ = "sale_items"
    __table_args__ = (
        UniqueConstraint("sale_id", "product_id", name="uq_sale_items_sale_product"),
        CheckConstraint("quantity > 0", name="ck_sale_items_quantity_positive"),
        CheckConstraint(
            "returned_quantity >= 0 AND returned_quantity <= quantity",
            name="ck_sale_items_returned_range",
        ),
    )

    sale_item_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(Uuid(as_uuid=True), ForeignKey("sales.sale_id"), nullable=False, index=True)
    product_id = Column(Uuid(as_uuid=True), ForeignKey("products.product_id"), nullable=False, index=True)

    product_name = Column(String(200), nullable=False)
    barcode = Column(String(64), nullable=True) 
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=False, default=_ZERO)
    quantity = Column(Integer, nullable=False)

    discount_percent = Column(Numeric(5, 2), nullable=True)  
    discount_amount = Column(Numeric(12, 2), nullable=False, default=_ZERO)  

    line_subtotal = Column(Numeric(12, 2), nullable=False, default=_ZERO) 
    tax_amount = Column(Numeric(12, 2), nullable=False, default=_ZERO)
    line_total = Column(Numeric(12, 2), nullable=False, default=_ZERO)    

    returned_quantity = Column(Integer, nullable=False, default=0)
    refunded_total = Column(Numeric(12, 2), nullable=False, default=_ZERO)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")