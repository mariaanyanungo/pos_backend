import uuid

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.sale import (
    CheckoutRequest,
    CheckoutResponse,
    RefundRequest,
    RefundResponse,
    SaleCreate,
    SaleRead,
    VoidRequest,
)
from app.services.checkout import checkout_service
from app.services.sale import sale_service
from database import get_db

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(
    data: SaleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return sale_service.create_sale(db, data, user)


@router.get("", response_model=list[SaleRead])
def list_sales(
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return sale_service.list_sales(
        db, user, status_filter=status_filter, skip=skip, limit=limit
    )


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(
    sale_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return sale_service.get_sale(db, sale_id, user)


@router.post("/{sale_id}/checkout", response_model=CheckoutResponse)
def checkout(
    sale_id: uuid.UUID,
    data: CheckoutRequest,
    response: Response,
    idempotency_key: str = Header(
        ..., alias="Idempotency-Key", min_length=1, max_length=255
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """201 on first execution, 200 (+ `Idempotent-Replay: true`) when the same
    Idempotency-Key is replayed. Card decline -> 402, insufficient stock -> 409."""
    result = checkout_service.checkout(db, sale_id, data, idempotency_key, user)
    if result.replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    else:
        response.status_code = status.HTTP_201_CREATED
    return {"sale": result.sale, "payment": result.payment, "receipt": result.receipt}


@router.post("/{sale_id}/void", response_model=SaleRead)
def void_sale(
    sale_id: uuid.UUID,
    data: VoidRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return sale_service.void_sale(db, sale_id, data.reason if data else None, user)


@router.post("/{sale_id}/refund", response_model=RefundResponse)
def refund_sale(
    sale_id: uuid.UUID,
    data: RefundRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sale, payment, refunded_amount = sale_service.refund_sale(db, sale_id, data, user)
    return {"sale": sale, "payment": payment, "refunded_amount": refunded_amount}
