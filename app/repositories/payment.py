import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PaymentStatus
from app.models.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self):
        super().__init__(Payment)

    def get_by_idempotency_key(self, db: Session, key: str) -> Payment | None:
        return db.scalar(select(Payment).where(Payment.idempotency_key == key))

    def get_captured_for_sale(self, db: Session, sale_id: uuid.UUID) -> Payment | None:
        stmt = select(Payment).where(
            Payment.sale_id == sale_id,
            Payment.status == PaymentStatus.CAPTURED.value,
        )
        return db.scalar(stmt)

    def search(
        self,
        db: Session,
        *,
        sale_id: uuid.UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        filters: dict[str, Any] = {"sale_id": sale_id, "status": status}
        return self.get_all(db, skip=skip, limit=limit, filters=filters)


payment_repository = PaymentRepository()
