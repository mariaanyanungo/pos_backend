import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, require_manager
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    StockAdjustmentCreate,
    StockMovementRead,
)
from app.services import inventory as inventory_service
from app.services.product import product_service
from database import get_db

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ProductRead])
def list_products(
    category_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    brand_name: str | None = None,
    name: str | None = Query(default=None, description="Case-insensitive substring match"),
    include_inactive: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return product_service.list_products(
        db,
        category_id=category_id,
        supplier_id=supplier_id,
        brand_name=brand_name,
        name=name,
        include_inactive=include_inactive,
        skip=skip,
        limit=limit,
    )


@router.get("/barcode/{barcode}", response_model=ProductRead)
def get_product_by_barcode(barcode: str, db: Session = Depends(get_db)):
    return product_service.get_product_by_barcode(db, barcode)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return product_service.get_product(db, product_id)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    return product_service.create_product(db, data, user)


@router.put("/{product_id}", response_model=ProductRead, dependencies=[Depends(require_manager)])
def update_product(product_id: uuid.UUID, data: ProductUpdate, db: Session = Depends(get_db)):
    return product_service.update_product(db, product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product_service.delete_product(db, product_id)


@router.post("/{product_id}/stock-adjustments", response_model=ProductRead)
def adjust_stock(
    product_id: uuid.UUID,
    data: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return inventory_service.manual_adjustment(db, product_id, data.quantity_change, data.reason, data.note, user)


@router.get(
    "/{product_id}/stock-movements",
    response_model=list[StockMovementRead],
    dependencies=[Depends(require_manager)],
)
def list_stock_movements(
    product_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return inventory_service.list_movements(db, product_id, skip=skip, limit=limit)


















