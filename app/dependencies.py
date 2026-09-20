from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from app.services.auth_service import get_user_from_token

auth2_scheme=OAuth2PasswordBearer(tokenUrl="/auth/login/")

def get_current_user(token:str=Depends(auth2_scheme), db:Session=Depends(get_db)):
    user=get_user_from_token(db,token)
    return user 