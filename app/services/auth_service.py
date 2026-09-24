import uuid
from typing import Any

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import UserRole
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import user_repository
from app.schemas.user import UserCreate, UserRegister
from app.services import user as user_service

_DUMMY_HASH = hash_password("timing-equaliser-password")


def register(db: Session, data: UserRegister) -> User:
    """Public sign-up. Always creates a plain cashier - roles are never client-controlled."""
    payload = UserCreate(**data.model_dump(), role=UserRole.CASHIER)
    return user_service.create_user(db, payload)


def authentication(db: Session, username: str, password: str) -> dict[str, str]:
    user = user_repository.get_by_username(db, username.strip().lower())
    hashed = user.hashed_password if user else _DUMMY_HASH
    password_ok = verify_password(password, hashed)
    if not user or not password_ok or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user.user_id), "token_type": "bearer"}


def get_user_from_token(db: Session, token: str) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = decode_access_token(token)
        user_id = uuid.UUID(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
        raise credentials_error

    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )
    return user


def bootstrap_admin(db: Session) -> User | None:
    """Creates the first admin from BOOTSTRAP_ADMIN_* env vars (idempotent)."""
    username = settings.bootstrap_admin_username
    email = settings.bootstrap_admin_email
    password = settings.bootstrap_admin_password
    if not (username and email and password):
        return None
    if user_repository.get_by_username(db, username.strip().lower()):
        return None
    payload = UserCreate(
        username=username,
        email=email,
        password=password,
        title="Administrator",
        role=UserRole.ADMIN,
    )
    return user_service.create_user(db, payload)
