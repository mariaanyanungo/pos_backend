from fastapi import APIRouter, Depends, status
from database import get_db
from app.schemas.user import UserCreate, UserRead, UserUpdate
from sqlalchemy.orm import Session
from app.services.user import user_service
import uuid

router=APIRouter( prefix="/users", tags=["users"])

@router.get("/", response_model=list[UserRead])
def list_users(db:Session=Depends(get_db)):
    return user_service.list_users(db)

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id:uuid.UUID, db:Session=Depends(get_db)):
    return user_service.get_user(db, user_id)

@router.post("/", response_model=UserRead)
def create_user(data:UserCreate, db:Session=Depends(get_db)):
    return user_service.create_user(db, data)

@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id:uuid.UUID, data:UserUpdate, db:Session=Depends(get_db)):
    return user_service.update_user(db, user_id, data)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id:uuid.UUID, db:Session=Depends(get_db)):
    return user_service.delete_user(db, user_id)





































