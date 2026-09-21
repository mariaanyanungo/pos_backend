import uuid
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.repositories.supplier import supplier_repository
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.common import conflict_on_integrity_error, get_or_404


def get_supplier(db: Session, supplier_id: uuid.UUID):
    return get_or_404(supplier_repository, db, supplier_id, "Supplier")


def list_suppliers(db: Session, *, skip: int = 0, limit: int = 100, include_inactive: bool = False):
    return supplier_repository.get_all(db, skip=skip, limit=limit, include_inactive=include_inactive)


def create_supplier(db: Session, data: SupplierCreate):
    with conflict_on_integrity_error(db, "A supplier with this email already exists"):
        supplier = supplier_repository.create(db, data.model_dump())
        db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(db: Session, supplier_id: uuid.UUID, data: SupplierUpdate):
    supplier = get_supplier(db, supplier_id)
    with conflict_on_integrity_error(db, "A supplier with this email already exists"):
        supplier_repository.update(db, supplier, data.model_dump(exclude_unset=True))
        db.commit()
    db.refresh(supplier)
    return supplier


def delete_supplier(db: Session, supplier_id: uuid.UUID) -> None:
    supplier = get_supplier(db, supplier_id)
    supplier_repository.update(db, supplier, {"is_active": False})
    db.commit()


supplier_service = SimpleNamespace(
    get_supplier=get_supplier,
    list_suppliers=list_suppliers,
    create_supplier=create_supplier,
    update_supplier=update_supplier,
    delete_supplier=delete_supplier,
)
