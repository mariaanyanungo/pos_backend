from app.models.supplier import Supplier
from sqlalchemy.orm import Session

class supplierRepository:
    
    def __init__(self):
        self.model=Supplier

    def get(self,db:Session, id:int):
        return db.get(Supplier, id)

    def get_all(self,db:Session):
        return db.query(Supplier).all()

    def create(self,db:Session, data:dict):
        supplier=supplier(**data)
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        return supplier

    def update(self, db:Session, db_obj:Supplier, data:dict):
        for field, value in data.items():
            setattr(db_obj, field,value)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def delete(self, db:Session, db_obj:Supplier):
        db.delete(db_obj)
        db.commit()

supplier_repository=supplierRepository()


    


