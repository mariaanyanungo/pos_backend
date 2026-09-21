import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, require_manager
from app.models.user import User
from app.schemas.receipt import ReceiptRead
from app.services.receipt import receipt_service
from database import get_db

# Receipts are issued by checkout and are immutable, so this router is read-only.
router = APIRouter(prefix="/receipts", tags=["receipts"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ReceiptRead], dependencies=[Depends(require_manager)])
def list_receipts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return receipt_service.list_receipts(db, skip=skip, limit=limit)


@router.get("/by-sale/{sale_id}", response_model=ReceiptRead)
def get_receipt_for_sale(sale_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return receipt_service.get_receipt_for_sale(db, sale_id, user)


@router.get("/{receipt_id}", response_model=ReceiptRead)
def get_receipt(receipt_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return receipt_service.get_receipt(db, receipt_id, user)
























