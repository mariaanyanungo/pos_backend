from fastapi import APIRouter, Depends, status
from database import get_db
from app.schemas.sale_item import Sale_itemCreate, Sale_itemRead, Sale_itemUpdate
from sqlalchemy.orm import Session
from app.services.sale_item import sale_item_service
import uuid

router=APIRouter( prefix="/sale_items", tags=["sale_items"])

@router.get("/", response_model=list[Sale_itemRead])
def list_sale_items(db:Session=Depends(get_db)):
    return sale_item_service.list_sale_items(db)

@router.get("/{sale_item_id}", response_model=Sale_itemRead)
def get_sale_item(sale_item_id:uuid.UUID, db:Session=Depends(get_db)):
    return sale_item_service.get_sale_item(db, sale_item_id)

@router.post("/", response_model=Sale_itemRead)
def create_sale_item(data:Sale_itemCreate, db:Session=Depends(get_db)):
    return sale_item_service.create_sale_item(db, data)

@router.put("/{sale_item_id}", response_model=Sale_itemRead)
def update_sale_item(sale_item_id:uuid.UUID, data:Sale_itemUpdate, db:Session=Depends(get_db)):
    return sale_item_service.update_sale_item(db, sale_item_id, data)

@router.delete("/{sale_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale_item(sale_item_id:uuid.UUID, db:Session=Depends(get_db)):
    return sale_item_service.delete_sale_item(db, sale_item_id)





































