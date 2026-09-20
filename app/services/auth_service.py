from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password
)
from app.repositories.user import user_repository
from app.schemas.user import UserCreate

def register(db:Session, data:UserCreate):
    if user_repository.get_by_username(db, data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    values=data.model_dump(exclude={"password"})
    values["hashed_password"]=hash_password(data.password)
    return user_repository.create(db,values)


def authentication(db:Session, username:str, password:str):
    user=user_repository.get_by_username(db,username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="incorrect username or password",
            headers={"WWW-Authenticate":"Bearer"},
        )
    return{
        "access_token":create_access_token(user_id),
        "token_type":"bearer",
        
    }
    
def get_user_from_token(db:Session, token:str):
    credentials_error=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="incorrect username or password",
        headers={"WWW-Authenticate":"Bearer"},     
    )
    try:
        payload:dict[str,Any]=decode_access_token(token)
        subject=payload.get("sub")
        if not isinstance(subject,str) or not subject.strip():
            raise credentials_error
        user_id=int(subject)
        if user_id<=0:
            raise credentials_error
    except Exception as e:
        raise credentials_error
    
    user=user_repository.get_by_id(db, user_id)
    if user is None:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user account is inactive"
        )
    return user
    
    
        