import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self):
        super().__init__(Product)

    def get_by_barcode(self, db: Session, barcode: str) -> Product | None:
        return db.scalar(select(Product).where(Product.barcode == barcode))

    def search(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
        filters: dict[str, Any] | None = None,
        name_contains: str | None = None,
    ) -> list[Product]:
        query = self._query(include_inactive, filters)
        if name_contains:
            query = query.where(
                func.lower(Product.name).contains(
                    name_contains.lower(), autoescape=True
                )
            )
        return self._page(db, query, skip, limit)

    def count_active_in_category(self, db: Session, category_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.category_id == category_id, Product.is_active.is_(True))
        )
        return db.scalar(stmt) or 0

    def adjust_stock(
        self,
        db: Session,
        product_id: uuid.UUID,
        delta: int,
        *,
        require_active: bool = False,
    ) -> bool:
        """Atomically change stock by `delta` (single UPDATE ... WHERE stock + delta >= 0).

        Returns False - and changes nothing - when the result would be negative
        (or the product is inactive and `require_active` is set). Because the
        check and the write are one statement, two concurrent checkouts can never
        both take the last unit, without needing an explicit read-then-write lock.
        """
        stmt = update(Product).where(
            Product.product_id == product_id,
            Product.stock_quantity + delta >= 0,
        )
        if require_active:
            stmt = stmt.where(Product.is_active.is_(True))
        stmt = stmt.values(
            stock_quantity=Product.stock_quantity + delta
        ).execution_options(synchronize_session=False)
        return db.execute(stmt).rowcount == 1


product_repository = ProductRepository()
