from app.models.sale_item import Sale_item
from sqlalchemy.orm import Session

class sale_itemRepository:
    
    def __init__(self):
        self.model=Sale_item

    def get(self,db:Session, id:int):
        return db.get(Sale_item, id)

    def get_all(self,db:Session):
        return db.query(Sale_item).all()

    def create(self,db:Session, data:dict):
        sale_item=sale_item(**data)
        db.add(sale_item)
        db.commit()
        db.refresh(sale_item)
        return sale_item

    def update(self, db:Session, db_obj:Sale_item, data:dict):
        for field, value in data.items():
            setattr(db_obj, field,value)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def delete(self, db:Session, db_obj:Sale_item):
        db.delete(db_obj)
        db.commit()

sale_item_repository=sale_itemRepository()


    


