import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, require_manager
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.services.customer import customer_service
from database import get_db

# Cashiers look customers up and register new ones at the till; only managers deactivate them.
router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    return customer_service.list_customers(db, skip=skip, limit=limit, include_inactive=include_inactive)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    return customer_service.get_customer(db, customer_id)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    return customer_service.create_customer(db, data)


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: uuid.UUID, data: CustomerUpdate, db: Session = Depends(get_db)):
    return customer_service.update_customer(db, customer_id, data)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_customer(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    customer_service.delete_customer(db, customer_id)






























