import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory_movement import InventoryMovement
from app.repositories.base import BaseRepository


class InventoryMovementRepository(BaseRepository[InventoryMovement]):
    def __init__(self):
        super().__init__(InventoryMovement)

    def record(
        self,
        db: Session,
        *,
        product_id: uuid.UUID,
        quantity_change: int,
        reason: str,
        sale_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        note: str | None = None,
    ) -> InventoryMovement:
        return self.create(
            db,
            {
                "product_id": product_id,
                "quantity_change": quantity_change,
                "reason": reason,
                "sale_id": sale_id,
                "created_by": user_id,
                "note": note,
            },
        )

    def list_for_product(
        self, db: Session, product_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[InventoryMovement]:
        query = select(InventoryMovement).where(InventoryMovement.product_id == product_id)
        return self._page(db, query, skip, limit)


inventory_movement_repository = InventoryMovementRepository()