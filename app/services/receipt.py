from types import SimpleNamespace
from sqlalchemy.orm import Session
from app.repositories.receipt import receiptRepository
from fastapi import HTTPException, status
from app.schemas.receipt import ReceiptBase,ReceiptRead,ReceiptCreate, ReceiptUpdate


def get_receipt(db:Session, id:int):
    receipt= receipt.get(db,id)
    if not receipt:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="receipt not found"
        )

def list_receipts(db:Session):
    return receiptRepository.get_all(db)

def create_receipt(db: Session, data:ReceiptCreate):
    return receiptRepository.create(db, data.model_dump())

def update_receipt(db:Session, receipt_id:int, data:ReceiptUpdate):
    receipt=get_receipt(db, receipt_id)
    return receipt.update(db, receipt, data.model_dump(exclude_unset=True))
    
def delete_receipt(db:Session, receipt_id:int):
    receipt=get_receipt(db, receipt_id)
    receipt.delete(db,receipt)
    

receipt_service = SimpleNamespace(
    get_receipt=get_receipt,
    list_receipts=list_receipts,
    create_receipt=create_receipt,
    update_receipt=update_receipt,
    delete_receipt=delete_receipt
)