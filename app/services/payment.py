import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import PaymentStatus, UserRole
from app.core.money import money
from app.models.payment import Payment
from app.models.user import User
from app.repositories.payment import payment_repository
from app.repositories.sale import sale_repository
from app.services import payment_gateway
from app.services.common import get_or_404

# The payment state machine. Anything not listed here is an illegal transition.
ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {PaymentStatus.AUTHORIZED, PaymentStatus.FAILED},
    PaymentStatus.AUTHORIZED: {PaymentStatus.CAPTURED, PaymentStatus.FAILED},
    PaymentStatus.CAPTURED: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.REFUNDED: set(),
}


def transition(payment: Payment, new_status: PaymentStatus) -> Payment:
    current = PaymentStatus(payment.status)
    if new_status not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Illegal payment status transition: {current.value} -> {new_status.value}",
        )
    payment.status = new_status.value
    return payment


def refund(payment: Payment, amount) -> Payment:
    """Refund part or all of a captured payment through the gateway.

    The payment only becomes `refunded` once the whole amount has been returned;
    until then it stays `captured` and `refunded_amount` tracks progress.
    """
    amount = money(amount)
    if PaymentStatus(payment.status) is not PaymentStatus.CAPTURED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Only captured payments can be refunded"
        )
    if amount > money(payment.amount - payment.refunded_amount):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Refund exceeds the captured amount"
        )

    if amount > 0:
        try:
            result = payment_gateway.get_gateway(payment.payment_method).refund(
                payment.gateway_reference, amount
            )
        except payment_gateway.GatewayError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, detail="Payment gateway unavailable"
            ) from exc
        if not result.approved:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=result.failure_reason
                or "Refund was declined by the payment gateway",
            )

    payment.refunded_amount = money(payment.refunded_amount + amount)
    if payment.refunded_amount == money(payment.amount):
        transition(payment, PaymentStatus.REFUNDED)
    return payment


def mark_captured(payment: Payment) -> Payment:
    transition(payment, PaymentStatus.CAPTURED)
    payment.captured_at = datetime.now(timezone.utc)
    return payment


def _assert_can_view(db: Session, payment: Payment, user: User) -> None:
    if user.role in (UserRole.ADMIN.value, UserRole.MANAGER.value):
        return
    sale = sale_repository.get(db, payment.sale_id)
    if sale is None or sale.cashier_id != user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Payment not found")


def get_payment(db: Session, payment_id: uuid.UUID, user: User) -> Payment:
    payment = get_or_404(payment_repository, db, payment_id, "Payment")
    _assert_can_view(db, payment, user)
    return payment


def list_payments(
    db: Session,
    *,
    sale_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    return payment_repository.search(
        db, sale_id=sale_id, status=status_filter, skip=skip, limit=limit
    )


payment_service = SimpleNamespace(
    get_payment=get_payment,
    list_payments=list_payments,
)
