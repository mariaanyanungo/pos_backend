from fastapi import APIRouter, Depends, status
from database import get_db
from app.schemas.receipt import ReceiptCreate, ReceiptRead, ReceiptUpdate
from sqlalchemy.orm import Session
from app.services.receipt import receipt_service
import uuid

router=APIRouter( prefix="/receipts", tags=["receipts"])

@router.get("/", response_model=list[ReceiptRead])
def list_receipts(db:Session=Depends(get_db)):
    return receipt_service.list_receipts(db)

@router.get("/{receipt_id}", response_model=ReceiptRead)
def get_receipt(receipt_id:uuid.UUID, db:Session=Depends(get_db)):
    return receipt_service.get_receipt(db, receipt_id)

@router.post("/", response_model=ReceiptRead)
def create_receipt(data:ReceiptCreate, db:Session=Depends(get_db)):
    return receipt_service.create_receipt(db, data)

@router.put("/{receipt_id}", response_model=ReceiptRead)
def update_receipt(receipt_id:uuid.UUID, data:ReceiptUpdate, db:Session=Depends(get_db)):
    return receipt_service.update_receipt(db, receipt_id, data)

@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(receipt_id:uuid.UUID, db:Session=Depends(get_db)):
    return receipt_service.delete_receipt(db, receipt_id)





































