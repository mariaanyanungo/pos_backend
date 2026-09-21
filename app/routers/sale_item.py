import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.sale import SaleRead
from app.schemas.sale_item import SaleItemCreate, SaleItemUpdate
from app.services.sale_item import sale_item_service
from database import get_db

router = APIRouter(prefix="/sales/{sale_id}/items", tags=["sale_items"])


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def add_item(
    sale_id: uuid.UUID,
    data: SaleItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return sale_item_service.add_item(db, sale_id, data, user)


@router.patch("/{item_id}", response_model=SaleRead)
def update_item(
    sale_id: uuid.UUID,
    item_id: uuid.UUID,
    data: SaleItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return sale_item_service.update_item(db, sale_id, item_id, data, user)


@router.delete("/{item_id}", response_model=SaleRead)
def remove_item(
    sale_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return sale_item_service.remove_item(db, sale_id, item_id, user)

























