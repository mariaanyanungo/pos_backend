import uuid
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.category import category_repository
from app.repositories.product import product_repository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.common import conflict_on_integrity_error, get_or_404


def get_category(db: Session, category_id: uuid.UUID):
    return get_or_404(category_repository, db, category_id, "Category")


def list_categories(
    db: Session, *, skip: int = 0, limit: int = 100, include_inactive: bool = False
):
    return category_repository.get_all(
        db, skip=skip, limit=limit, include_inactive=include_inactive
    )


def create_category(db: Session, data: CategoryCreate):
    with conflict_on_integrity_error(db, "A category with this name already exists"):
        category = category_repository.create(db, data.model_dump())
        db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: uuid.UUID, data: CategoryUpdate):
    category = get_category(db, category_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_active") is False:
        _ensure_no_active_products(db, category_id)
    with conflict_on_integrity_error(db, "A category with this name already exists"):
        category_repository.update(db, category, changes)
        db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: uuid.UUID) -> None:
    """Soft delete: products and historic sales keep pointing at the row."""
    category = get_category(db, category_id)
    _ensure_no_active_products(db, category_id)
    category_repository.update(db, category, {"is_active": False})
    db.commit()


def _ensure_no_active_products(db: Session, category_id: uuid.UUID) -> None:
    if product_repository.count_active_in_category(db, category_id) > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Category still has active products; move or deactivate them first",
        )


category_service = SimpleNamespace(
    get_category=get_category,
    list_categories=list_categories,
    create_category=create_category,
    update_category=update_category,
    delete_category=delete_category,
)
