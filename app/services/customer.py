import uuid
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.repositories.customer import customer_repository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.common import conflict_on_integrity_error, get_or_404


def get_customer(db: Session, customer_id: uuid.UUID):
    return get_or_404(customer_repository, db, customer_id, "Customer")


def list_customers(db: Session, *, skip: int = 0, limit: int = 100, include_inactive: bool = False):
    return customer_repository.get_all(db, skip=skip, limit=limit, include_inactive=include_inactive)


def create_customer(db: Session, data: CustomerCreate):
    with conflict_on_integrity_error(db, "A customer with this email already exists"):
        customer = customer_repository.create(db, data.model_dump())
        db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer_id: uuid.UUID, data: CustomerUpdate):
    customer = get_customer(db, customer_id)
    with conflict_on_integrity_error(db, "A customer with this email already exists"):
        customer_repository.update(db, customer, data.model_dump(exclude_unset=True))
        db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: uuid.UUID) -> None:
    customer = get_customer(db, customer_id)
    customer_repository.update(db, customer, {"is_active": False})
    db.commit()


customer_service = SimpleNamespace(
    get_customer=get_customer,
    list_customers=list_customers,
    create_customer=create_customer,
    update_customer=update_customer,
    delete_customer=delete_customer,
)
