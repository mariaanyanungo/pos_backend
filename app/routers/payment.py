import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, require_manager
from app.models.user import User
from app.schemas.payment import PaymentRead
from app.services.payment import payment_service
from database import get_db


router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[PaymentRead], dependencies=[Depends(require_manager)])
def list_payments(
    sale_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return payment_service.list_payments(db, sale_id=sale_id, status_filter=status_filter, skip=skip, limit=limit)


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return payment_service.get_payment(db, payment_id, user)
































