from types import SimpleNamespace

from sqlalchemy.orm import Session
from app.repositories.sale_item import sale_itemRepository
from fastapi import HTTPException, status
from app.schemas.sale_item import Sale_itemBase,Sale_itemRead,Sale_itemCreate, Sale_itemUpdate


def get_sale_item(db:Session, id:int):
    sale_item= sale_item.get(db,id)
    if not sale_item:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="sale_item not found"
        )

def list_sale_items(db:Session):
    return sale_itemRepository.get_all(db)

def create_sale_item(db: Session, data:Sale_itemCreate):
    return sale_itemRepository.create(db, data.model_dump())

def update_sale_item(db:Session, sale_item_id:int, data:Sale_itemUpdate):
    sale_item=get_sale_item(db, sale_item_id)
    return sale_item.update(db, sale_item, data.model_dump(exclude_unset=True))
    
def delete_sale_item(db:Session, sale_item_id:int):
    sale_item=get_sale_item(db, sale_item_id)
    sale_item.delete(db,sale_item)
    
    
sale_item_service = SimpleNamespace(
    get_sale_item=get_sale_item,
    list_sale_items=list_sale_items,
    create_sale_item=create_sale_item,
    update_sale_item=update_sale_item,
    delete_sale_item=delete_sale_item
)

