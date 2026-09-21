from contextlib import contextmanager

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError


def get_or_404(repo, db, obj_id, label: str):
    obj = repo.get(db, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return obj


@contextmanager
def conflict_on_integrity_error(db, detail: str):
    """Turn unique-constraint violations into a clean 409 and roll the session back."""
    try:
        yield
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=detail) from exc