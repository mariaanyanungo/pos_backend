from app.models.user import User
from sqlalchemy.orm import Session

class userRepository:
    
    def __init__(self):
        self.model=User

    def get_by_id(self,db:Session, user_id:int):
        return db.query(User).filter(User.user_id==user_id).first()
    
    
    def get_by_username(self,db:Session, username:str):
        return db.get(User, username)

    def get_all(self,db:Session):
        return db.query(User).all()

    def create(self,db:Session, data:dict):
        user=user(**data)                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update(self, db:Session, db_obj:User, data:dict):
        for field, value in data.items():
            setattr(db_obj, field,value)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def delete(self, db:Session, db_obj:User):
        db.delete(db_obj)
        db.commit()

user_repository=userRepository()


    


