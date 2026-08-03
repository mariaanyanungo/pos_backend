
from app.models.payment import Payment
from sqlalchemy.orm import Session

class paymentRepository:
    
    def __init__(self):
        self.model=Payment

    def get(self,db:Session, id:int):
        return db.get(Payment, id)

    def get_all(self,db:Session):
        return db.query(Payment).all()

    def create(self,db:Session, data:dict):
        payment=payment(**data)
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    def update(self, db:Session, db_obj:Payment, data:dict):
        for field, value in data.items():
            setattr(db_obj, field,value)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def delete(self, db:Session, db_obj:Payment):
        db.delete(db_obj)
        db.commit()

payment_repository=paymentRepository()


    


