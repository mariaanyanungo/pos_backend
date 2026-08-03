from sqlalchemy.orm import Session
from app.repositories.category import categoryRepository
from fastapi import HTTPException, status
from app.schemas.category import CategoryBase,CategoryRead,CategoryCreate, CategoryUpdate
from types import SimpleNamespace


def get_category(db:Session, id:int):
    category= category.get(db,id)
    if not category:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="category not found"
        )

def list_categorys(db:Session):
    return categoryRepository.get_all(db)

def create_category(db: Session, data:CategoryCreate):
    return categoryRepository.create(db, data.model_dump())

def update_category(db:Session, category_id:int, data:CategoryUpdate):
    category=get_category(db, category_id)
    return category.update(db, category, data.model_dump(exclude_unset=True))
    
def delete_category(db:Session, category_id:int):
    category=get_category(db, category_id)
    category.delete(db,category)
    
category_service = SimpleNamespace(
    get_category=get_category,
    list_categorys=list_categorys,
    create_category=create_category,
    update_category=update_category,
    delete_category=delete_category
)

