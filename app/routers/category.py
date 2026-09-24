import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, require_manager
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.category import category_service
from database import get_db

router = APIRouter(
    prefix="/categories", tags=["categories"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[CategoryRead])
def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    return category_service.list_categories(
        db, skip=skip, limit=limit, include_inactive=include_inactive
    )


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    return category_service.get_category(db, category_id)


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_manager)],
)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return category_service.create_category(db, data)


@router.put(
    "/{category_id}",
    response_model=CategoryRead,
    dependencies=[Depends(require_manager)],
)
def update_category(
    category_id: uuid.UUID, data: CategoryUpdate, db: Session = Depends(get_db)
):
    return category_service.update_category(db, category_id, data)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_manager)],
)
def delete_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    category_service.delete_category(db, category_id)
