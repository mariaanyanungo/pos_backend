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

class Sale_item(Base):
    __tablename__ = "sale_items"

    sale_item_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.sale_id"), nullable=False)
    barcode = Column(String, unique=True, nullable=False, index=True)   
    unit_price = Column(Numeric(10, 2), nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sale=relationship("Sale", back_populates="sale_items")