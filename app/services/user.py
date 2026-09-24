import uuid
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user import user_repository
from app.schemas.user import UserCreate, UserUpdate
from app.services.common import conflict_on_integrity_error, get_or_404


def get_user(db: Session, user_id: uuid.UUID):
    return get_or_404(user_repository, db, user_id, "User")


def list_users(
    db: Session, *, skip: int = 0, limit: int = 100, include_inactive: bool = False
):
    return user_repository.get_all(
        db, skip=skip, limit=limit, include_inactive=include_inactive
    )


def _ensure_unique(
    db: Session,
    *,
    username: str | None = None,
    email: str | None = None,
    exclude_id=None,
):
    if username:
        existing = user_repository.get_by_username(db, username)
        if existing and existing.user_id != exclude_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Username already taken"
            )
    if email:
        existing = user_repository.get_by_email(db, email)
        if existing and existing.user_id != exclude_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Email already registered"
            )


def create_user(db: Session, data: UserCreate):
    _ensure_unique(db, username=data.username, email=data.email)
    values = data.model_dump(exclude={"password"})
    values["hashed_password"] = hash_password(data.password)
    with conflict_on_integrity_error(db, "Username or email already in use"):
        user = user_repository.create(db, values)
        db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: uuid.UUID, data: UserUpdate, acting_user: User):
    user = get_user(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    _ensure_unique(db, email=changes.get("email"), exclude_id=user_id)

    if user.user_id == acting_user.user_id:
        if changes.get("is_active") is False:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="You cannot deactivate your own account",
            )
        if "role" in changes and changes["role"] != user.role:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="You cannot change your own role"
            )

    password = changes.pop("password", None)
    if password:
        changes["hashed_password"] = hash_password(password)

    with conflict_on_integrity_error(db, "Email already registered"):
        user_repository.update(db, user, changes)
        db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: uuid.UUID, acting_user: User) -> None:
    """Soft delete - sales keep referencing the cashier who made them."""
    user = get_user(db, user_id)
    if user.user_id == acting_user.user_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="You cannot deactivate your own account"
        )
    user_repository.update(db, user, {"is_active": False})
    db.commit()


user_service = SimpleNamespace(
    get_user=get_user,
    list_users=list_users,
    create_user=create_user,
    update_user=update_user,
    delete_user=delete_user,
)
