from sqlalchemy.orm import Session
from app.repositories.sale import saleRepository
from fastapi import HTTPException, status
from app.schemas.sale import SaleBase,SaleRead,SaleCreate, SaleUpdate
from types import SimpleNamespace


def get_sale(db:Session, id:int):
    sale= sale.get(db,id)
    if not sale:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="sale not found"
        )

def list_sales(db:Session):
    return saleRepository.get_all(db)

def create_sale(db: Session, data:SaleCreate):
    return saleRepository.create(db, data.model_dump())

def update_sale(db:Session, sale_id:int, data:SaleUpdate):
    sale=get_sale(db, sale_id)
    return sale.update(db, sale, data.model_dump(exclude_unset=True))
    
def delete_sale(db:Session, sale_id:int):
    sale=get_sale(db, sale_id)
    sale.delete(db,sale)
    

sale_service = SimpleNamespace(
    get_sale=get_sale,
    list_sales=list_sales,
    create_sale=create_sale,
    update_sale=update_sale,
    delete_sale=delete_sale
)