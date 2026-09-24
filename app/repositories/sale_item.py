import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sale_item import SaleItem
from app.repositories.base import BaseRepository


class SaleItemRepository(BaseRepository[SaleItem]):
    def __init__(self):
        super().__init__(SaleItem)

    def get_by_sale_and_product(
        self, db: Session, sale_id: uuid.UUID, product_id: uuid.UUID
    ) -> SaleItem | None:
        stmt = select(SaleItem).where(
            SaleItem.sale_id == sale_id, SaleItem.product_id == product_id
        )
        return db.scalar(stmt)


sale_item_repository = SaleItemRepository()
