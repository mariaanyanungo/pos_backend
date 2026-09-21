import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import require_manager
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services.supplier import supplier_service
from database import get_db

# Supplier data (contacts, addresses) is back-office only.
router = APIRouter(prefix="/suppliers", tags=["suppliers"], dependencies=[Depends(require_manager)])


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    return supplier_service.list_suppliers(db, skip=skip, limit=limit, include_inactive=include_inactive)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: uuid.UUID, db: Session = Depends(get_db)):
    return supplier_service.get_supplier(db, supplier_id)


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    return supplier_service.create_supplier(db, data)


@router.put("/{supplier_id}", response_model=SupplierRead)
def update_supplier(supplier_id: uuid.UUID, data: SupplierUpdate, db: Session = Depends(get_db)):
    return supplier_service.update_supplier(db, supplier_id, data)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: uuid.UUID, db: Session = Depends(get_db)):
    supplier_service.delete_supplier(db, supplier_id)






























