from sqlalchemy import(
    Column,
    Integer,
    String, 
    Boolean, 
    ForeignKey,
    DateTime,
    ForeignKey  
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID


from database import Base

class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.payment_id"), nullable=False)
    quantity = Column(UUID(as_uuid=True), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), nullable=True, default=0)
    vat = Column(Numeric(10, 2), nullable=True, default=0)
    change = Column(Numeric(10, 2), nullable=True, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    item_price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)

    payment = relationship("Payment", back_populates="receipts")
  
 
   

   