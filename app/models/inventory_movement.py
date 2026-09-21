import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.sql import func

from database import Base


class InventoryMovement(Base):
    """Append-only stock ledger. `products.stock_quantity` is the fast running
    balance; this table explains every change to it."""

    __tablename__ = "inventory_movements"

    movement_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(Uuid(as_uuid=True), ForeignKey("products.product_id"), nullable=False, index=True)
    sale_id = Column(Uuid(as_uuid=True), ForeignKey("sales.sale_id"), nullable=True, index=True)
    quantity_change = Column(Integer, nullable=False)  # negative = stock out
    reason = Column(String(30), nullable=False)
    note = Column(String(500), nullable=True)
    created_by = Column(Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)