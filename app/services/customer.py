from sqlalchemy.orm import Session
from app.repositories.customer import customerRepository
from fastapi import HTTPException, status
from app.schemas.customer import CustomerBase,CustomerRead,CustomerCreate, CustomerUpdate
from types import SimpleNamespace


def get_customer(db:Session, id:int):
    customer= customer.get(db,id)
    if not customer:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="customer not found"
        )

def list_customers(db:Session):
    return customerRepository.get_all(db)

def create_customer(db: Session, data:CustomerCreate):
    return customerRepository.create(db, data.model_dump())

def update_customer(db:Session, customer_id:int, data:CustomerUpdate):
    customer=get_customer(db, customer_id)
    return customer.update(db, customer, data.model_dump(exclude_unset=True))
    
def delete_customer(db:Session, customer_id:int):
    customer=get_customer(db, customer_id)
    customer.delete(db,customer)
    
    
customer_service = SimpleNamespace(
    get_customer=get_customer,
    list_customers=list_customers,
    create_customer=create_customer,
    update_customer=update_customer,
    delete_customer=delete_customer
)
    

