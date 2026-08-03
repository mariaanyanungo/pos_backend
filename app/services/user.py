from sqlalchemy.orm import Session
from app.repositories.user import userRepository
from fastapi import HTTPException, status
from app.schemas.user import UserBase,UserRead,UserCreate, UserUpdate
from types import SimpleNamespace


def get_user(db:Session, id:int):
    user= user.get(db,id)
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="user not found"
        )

def list_users(db:Session):
    return userRepository.get_all(db)

def create_user(db: Session, data:UserCreate):
    return userRepository.create(db, data.model_dump())

def update_user(db:Session, user_id:int, data:UserUpdate):
    user=get_user(db, user_id)
    return user.update(db, user, data.model_dump(exclude_unset=True))
    
def delete_user(db:Session, user_id:int):
    user=get_user(db, user_id)
    user.delete(db,user)
    
user_service = SimpleNamespace(
    get_user=get_user,
    list_users=list_users,
    create_user=create_user,
    update_user=update_user,
    delete_user=delete_user
)
    

