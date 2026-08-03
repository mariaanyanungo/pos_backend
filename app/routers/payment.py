from fastapi import APIRouter, Depends, status
from database import get_db
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate
from sqlalchemy.orm import Session
from app.services.payment import payment_service
import uuid

router=APIRouter( prefix="/payments", tags=["payments"])

@router.get("/", response_model=list[PaymentRead])
def list_payments(db:Session=Depends(get_db)):
    return payment_service.list_payments(db)

@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id:uuid.UUID, db:Session=Depends(get_db)):
    return payment_service.get_payment(db, payment_id)

@router.post("/", response_model=PaymentRead)
def create_payment(data:PaymentCreate, db:Session=Depends(get_db)):
    return payment_service.create_payment(db, data)

@router.put("/{payment_id}", response_model=PaymentRead)
def update_payment(payment_id:uuid.UUID, data:PaymentUpdate, db:Session=Depends(get_db)):
    return payment_service.update_payment(db, payment_id, data)

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id:uuid.UUID, db:Session=Depends(get_db)):
    return payment_service.delete_payment(db, payment_id)





































