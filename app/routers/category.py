from fastapi import APIRouter, Depends, status
from database import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from sqlalchemy.orm import Session
from app.services.category import category_service
import uuid

router=APIRouter( prefix="/categorys", tags=["categorys"])

@router.get("/", response_model=list[CategoryRead])
def list_categorys(db:Session=Depends(get_db)):
    return category_service.list_categorys(db)

@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id:uuid.UUID, db:Session=Depends(get_db)):
    return category_service.get_category(db, category_id)

@router.post("/", response_model=CategoryRead)
def create_category(data:CategoryCreate, db:Session=Depends(get_db)):
    return category_service.create_category(db, data)

@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id:uuid.UUID, data:CategoryUpdate, db:Session=Depends(get_db)):
    return category_service.update_category(db, category_id, data)

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id:uuid.UUID, db:Session=Depends(get_db)):
    return category_service.delete_category(db, category_id)





































