from sqlalchemy.orm import Session
from app.repositories.supplier import supplierRepository
from fastapi import HTTPException, status
from app.schemas.supplier import SupplierBase,SupplierRead,SupplierCreate, SupplierUpdate
from types import SimpleNamespace


def get_supplier(db:Session, id:int):
    supplier= supplier.get(db,id)
    if not supplier:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="supplier not found"
        )

def list_suppliers(db:Session):
    return supplierRepository.get_all(db)

def create_supplier(db: Session, data:SupplierCreate):
    return supplierRepository.create(db, data.model_dump())

def update_supplier(db:Session, supplier_id:int, data:SupplierUpdate):
    supplier=get_supplier(db, supplier_id)
    return supplier.update(db, supplier, data.model_dump(exclude_unset=True))
    
def delete_supplier(db:Session, supplier_id:int):
    supplier=get_supplier(db, supplier_id)
    supplier.delete(db,supplier)
    
supplier_service = SimpleNamespace(
    get_supplier=get_supplier,
    list_suppliers=list_suppliers,
    create_supplier=create_supplier,
    update_supplier=update_supplier,
    delete_supplier=delete_supplier
)
    

