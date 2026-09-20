from types import SimpleNamespace
from sqlalchemy.orm import Session
from app.repositories.product import ProductRepository
from fastapi import HTTPException, status
from app.schemas.product import ProductBase,ProductRead,ProductCreate, ProductUpdate
import uuid


def get_product(db:Session, product_id:uuid.UUID):
    product=product.get(db,product_id)
    if not product:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

def list_products(data, db:Session):
    return ProductRepository.get_all(db, data.model_dump())

def create_product(db: Session, data:ProductCreate):
    return ProductRepository.create(db, data.model_dump())

def update_product(db:Session, product_id:uuid.UUID, data:ProductUpdate):
    product=get_product(db, product_id)
    return ProductRepository.update(db, product, data.model_dump(exclude_unset=True))
    
def delete_product(db:Session, product_id:uuid.UUID):
    product=get_product(db, product_id)
    ProductRepository.delete(db, product)
    
    
product_service = SimpleNamespace(
    get_product=get_product,
    list_products=list_products,
    create_product=create_product,
    update_product=update_product,
    delete_product=delete_product
)
    

