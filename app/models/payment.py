from sqlalchemy import(
    Column,
    Integer,
    String, 
    Boolean, 
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID

from database import Base

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    sale_item_id = Column(UUID(as_uuid=True), ForeignKey("sale_items.sale_item_id"), nullable=False)
    payment_method = Column(String, nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sales_item = relationship("SaleItems", back_populates="payments")