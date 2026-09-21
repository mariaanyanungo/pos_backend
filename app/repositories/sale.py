

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.sale import Sale
from app.repositories.base import BaseRepository


class SaleRepository(BaseRepository[Sale]):
    def __init__(self):
        super().__init__(Sale)

    def get_with_items(self, db: Session, sale_id: uuid.UUID) -> Sale | None:
        stmt = select(Sale).options(selectinload(Sale.items)).where(Sale.sale_id == sale_id)
        return db.scalar(stmt)

    def get_for_update(self, db: Session, sale_id: uuid.UUID) -> Sale | None:
        """Row-locks the sale (SELECT ... FOR UPDATE on PostgreSQL) so checkout,
        void, refund and cart edits on the same sale are serialised."""
        stmt = (
            select(Sale)
            .options(selectinload(Sale.items))
            .where(Sale.sale_id == sale_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return db.scalar(stmt)

    def search(
        self,
        db: Session,
        *,
        cashier_id: uuid.UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Sale]:
        stmt = select(Sale).options(selectinload(Sale.items))
        if cashier_id is not None:
            stmt = stmt.where(Sale.cashier_id == cashier_id)
        if status is not None:
            stmt = stmt.where(Sale.status == status)
        stmt = stmt.order_by(Sale.created_at.desc(), Sale.sale_id).offset(skip).limit(limit)
        return list(db.scalars(stmt))


sale_repository = SaleRepository()