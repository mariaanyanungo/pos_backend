
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.receipt import Receipt
from app.repositories.base import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    def __init__(self):
        super().__init__(Receipt)

    def get_by_sale_id(self, db: Session, sale_id: uuid.UUID) -> Receipt | None:
        return db.scalar(select(Receipt).where(Receipt.sale_id == sale_id))

    def get_by_number(self, db: Session, receipt_number: str) -> Receipt | None:
        return db.scalar(select(Receipt).where(Receipt.receipt_number == receipt_number))


receipt_repository = ReceiptRepository()
