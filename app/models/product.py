import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_products_tax_rate_range"),
      
        CheckConstraint("stock_quantity >= 0", name="ck_products_stock_non_negative"),
    )

    product_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    brand_name = Column(String(100), nullable=False)
    barcode = Column(String(64), unique=True, nullable=True, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))  # percent, e.g. 20.00
    stock_quantity = Column(Integer, nullable=False, default=0)
    category_id = Column(Uuid(as_uuid=True), ForeignKey("categories.category_id"), nullable=False, index=True)
    supplier_id = Column(Uuid(as_uuid=True), ForeignKey("suppliers.supplier_id"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")