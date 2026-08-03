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
import uuid
from sqlalchemy.dialects.postgresql import UUID


from database import Base

class Category(Base):
    __tablename__ = "categories"

    category_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    category_name = Column(String, nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="categories")
   