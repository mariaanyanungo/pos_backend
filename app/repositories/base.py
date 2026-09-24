from typing import Any, Generic, TypeVar

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Data access only. Repositories `flush` but never `commit`: the service
    layer owns the transaction so multi-step operations stay atomic."""

    def __init__(self, model: type[ModelT]):
        self.model = model
        self._pk = sa_inspect(model).primary_key[0]

    def get(self, db: Session, obj_id: Any) -> ModelT | None:
        return db.get(self.model, obj_id)

    def _query(
        self, include_inactive: bool = False, filters: dict[str, Any] | None = None
    ):
        query = select(self.model)
        if not include_inactive and hasattr(self.model, "is_active"):
            query = query.where(self.model.is_active.is_(True))
        for field, value in (filters or {}).items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)
        return query

    def _page(self, db: Session, query, skip: int, limit: int) -> list[ModelT]:
        query = (
            query.order_by(self.model.created_at, self._pk).offset(skip).limit(limit)
        )
        return list(db.scalars(query))

    def get_all(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> list[ModelT]:
        return self._page(db, self._query(include_inactive, filters), skip, limit)

    def create(self, db: Session, data: dict[str, Any]) -> ModelT:
        obj = self.model(**data)
        db.add(obj)
        db.flush()
        return obj

    def update(self, db: Session, db_obj: ModelT, data: dict[str, Any]) -> ModelT:
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.flush()
        return db_obj

    def delete(self, db: Session, db_obj: ModelT) -> None:
        db.delete(db_obj)
        db.flush()
