from fastapi import APIRouter, Depends, status
from database import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from sqlalchemy.orm import Session
from app.services.product import product_service
from app.repositories.product import product_repository
from app.models.product import Product

import uuid

router=APIRouter( prefix="/products", tags=["products"])

@router.get("/", response_model=list[ProductRead])
def list_products(data:ProductRead=None, db:Session=Depends(get_db)):
    return product_service.list_products(db,data)

@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id:uuid.UUID, db:Session=Depends(get_db)):
    return product_service.get_product(db, product_id)

@router.post("/", response_model=ProductRead)
def create_product(data:ProductCreate, db:Session=Depends(get_db)):
    return product_service.create_product(db, data)

@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id:uuid.UUID, data:ProductUpdate, db:Session=Depends(get_db)):
    return product_service.update_product(db, product_id, data)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id:uuid.UUID, db:Session=Depends(get_db)):
    return product_service.delete_product(db, product_id)





































