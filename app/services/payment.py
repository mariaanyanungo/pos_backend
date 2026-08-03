from sqlalchemy.orm import Session
from app.repositories.payment import paymentRepository
from fastapi import HTTPException, status
from app.schemas.payment import PaymentBase,PaymentRead,PaymentCreate, PaymentUpdate
from types import SimpleNamespace


def get_payment(db:Session, id:int):
    payment= payment.get(db,id)
    if not payment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="payment not found"
        )

def list_payments(db:Session):
    return paymentRepository.get_all(db)

def create_payment(db: Session, data:PaymentCreate):
    return paymentRepository.create(db, data.model_dump())

def update_payment(db:Session, payment_id:int, data:PaymentUpdate):
    payment=get_payment(db, payment_id)
    return payment.update(db, payment, data.model_dump(exclude_unset=True))
    
def delete_payment(db:Session, payment_id:int):
    payment=get_payment(db, payment_id)
    payment.delete(db,payment)
    
payment_service = SimpleNamespace(
    get_payment=get_payment,
    list_payments=list_payments,
    create_payment=create_payment,
    update_payment=update_payment,
    delete_payment=delete_payment
)
    

