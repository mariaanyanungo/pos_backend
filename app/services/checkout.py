import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import PaymentMethod, PaymentStatus, SaleStatus
from app.core.money import ZERO, money
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.sale import Sale
from app.models.user import User
from app.repositories.payment import payment_repository
from app.repositories.receipt import receipt_repository
from app.schemas.sale import CheckoutRequest
from app.services import inventory as inventory_svc
from app.services import payment as payment_svc
from app.services import payment_gateway
from app.services import receipt as receipt_svc
from app.services import sale as sale_svc


@dataclass
class CheckoutResult:
    sale: Sale
    payment: Payment
    receipt: Receipt | None
    replayed: bool = False


def _clean_key(key: str | None) -> str:
    key = (key or "").strip()
    if not key or len(key) > 255:
        raise HTTPException(
            422,
            detail="Idempotency-Key header is required (1-255 characters)",
        )
    return key


def _fingerprint(sale_id: uuid.UUID, data: CheckoutRequest) -> str:
    tendered = "" if data.amount_tendered is None else str(money(data.amount_tendered))
    raw = f"{sale_id}|{data.payment_method}|{tendered}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _resolve_tender(method: str, total: Decimal, tendered) -> tuple[Decimal, Decimal]:
    """Returns (amount_tendered, change_due) or raises 422."""
    if method == PaymentMethod.CASH:
        tendered = money(tendered)
        if tendered < total:
            raise HTTPException(
                422,
                detail=f"Insufficient cash tendered: total is {total}, received {tendered}",
            )
        return tendered, money(tendered - total)
    # Card: charged exactly the total. An explicit, different tender is a client bug.
    if tendered is not None and money(tendered) != total:
        raise HTTPException(
            422,
            detail="Card payments are charged the exact sale total; amount_tendered must match or be omitted",
        )
    return total, ZERO


def _replay(db: Session, payment: Payment, sale_id: uuid.UUID, fingerprint: str, user: User) -> CheckoutResult:
    if payment.sale_id != sale_id or payment.request_fingerprint != fingerprint:
        raise HTTPException(
            422,
            detail="Idempotency-Key was already used for a different request",
        )
    sale = sale_svc.get_sale(db, payment.sale_id, user)  # also enforces ownership
    if payment.status == PaymentStatus.FAILED.value:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail=payment.failure_reason or "Payment failed")
    receipt = receipt_repository.get_by_sale_id(db, sale.sale_id)
    return CheckoutResult(sale=sale, payment=payment, receipt=receipt, replayed=True)


def _record_failure(db: Session, values: dict, reason: str):
    """Undo everything the attempt did (stock, sale changes) and keep only an
    audit row saying the payment failed, under the caller's idempotency key."""
    db.rollback()
    payment_repository.create(db, {**values, "status": PaymentStatus.FAILED.value, "failure_reason": reason})
    db.commit()
    raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail=reason)


def checkout(
    db: Session,
    sale_id: uuid.UUID,
    data: CheckoutRequest,
    idempotency_key: str | None,
    user: User,
) -> CheckoutResult:
    """Pay for an open sale - all or nothing.

    Inside ONE transaction: lock sale -> reprice -> reserve/deduct stock ->
    authorize -> capture -> complete sale -> issue receipt -> commit.
    Any failure rolls the whole thing back, so we never end up with money taken
    but stock untouched (or the reverse).

    Idempotency: the same Idempotency-Key + same request returns the original
    outcome instead of charging twice; the same key with a different request is
    rejected.
    """
    key = _clean_key(idempotency_key)
    fingerprint = _fingerprint(sale_id, data)

    existing = payment_repository.get_by_idempotency_key(db, key)
    if existing is not None:
        return _replay(db, existing, sale_id, fingerprint, user)

    sale = sale_svc.get_sale(db, sale_id, user, for_update=True)

    existing = payment_repository.get_by_idempotency_key(db, key)
    if existing is not None:
        return _replay(db, existing, sale_id, fingerprint, user)

    try:
        sale_svc.require_status(sale, SaleStatus.OPEN, f"Sale is {sale.status}, not open for checkout")
        if not sale.items:
            raise HTTPException(422, detail="Cannot check out an empty sale")

        sale_svc.reprice(sale)
        total = money(sale.total_amount)
        tendered, change = _resolve_tender(data.payment_method, total, data.amount_tendered)
    except Exception:
        db.rollback()
        raise

    payment_values = {
        "sale_id": sale.sale_id,
        "amount": total,
        "amount_tendered": tendered,
        "change_due": change,
        "payment_method": data.payment_method,
        "idempotency_key": key,
        "request_fingerprint": fingerprint,
    }

    try:
        payment = payment_repository.create(db, {**payment_values, "status": PaymentStatus.PENDING.value})
    except IntegrityError:
      
        db.rollback()
        winner = payment_repository.get_by_idempotency_key(db, key)
        if winner is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="A request with this Idempotency-Key is already in progress",
            )
        return _replay(db, winner, sale_id, fingerprint, user)

    try:
        inventory_svc.deduct_for_sale(db, sale, user)
    except Exception:
        db.rollback()
        raise

    gateway = payment_gateway.get_gateway(data.payment_method)
    try:
        authorization = gateway.authorize(total, key)
        if not authorization.approved:
            _record_failure(db, payment_values, authorization.failure_reason or "Payment was declined")
        payment_svc.transition(payment, PaymentStatus.AUTHORIZED)
        payment.gateway_reference = authorization.reference

        capture = gateway.capture(authorization.reference, total)
        if not capture.approved:
            gateway.void(authorization.reference)
            _record_failure(db, payment_values, capture.failure_reason or "Payment capture failed")
    except payment_gateway.GatewayError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Payment gateway unavailable; retry with the same Idempotency-Key",
        ) from exc

    try:
        payment_svc.mark_captured(payment)
        sale.status = SaleStatus.COMPLETED.value
        sale.completed_at = datetime.now(timezone.utc)
        receipt = receipt_svc.issue_receipt(db, sale, payment)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(sale)
    db.refresh(payment)
    db.refresh(receipt)
    return CheckoutResult(sale=sale, payment=payment, receipt=receipt, replayed=False)


checkout_service = SimpleNamespace(checkout=checkout)