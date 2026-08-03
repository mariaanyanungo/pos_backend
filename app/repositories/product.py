from app.models.product import Product
from sqlalchemy.orm import Session
import uuid
from app.schemas.product import ProductRead
class ProductRepository:
    
    def __init__(self):
        self.model=Product

    def get(self,db:Session, product_id:uuid.UUID):
        return db.get(Product, product_id)

    def get_all(self,db:Session, data:ProductRead=None):
        query=db.query(Product)
        if data:
            for field, value in data.model_dump().items():
                if value is not None:
                    query=query.filter(getattr(Product, field)==value)
        return query.all()

    def create(self,db:Session, data:dict):
        product=Product(**data)
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    def update(self, db:Session, db_obj:Product, data:dict):
        for field, value in data.items():
            setattr(db_obj, field,value)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def delete(self, db:Session, db_obj:Product):
        db.delete(db_obj)
        db.commit()

product_repository=ProductRepository()


    


