import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.sale import Sale
from app.models.user import User
from app.repositories.receipt import receipt_repository
from app.repositories.sale import sale_repository
from app.services.common import get_or_404


def _new_receipt_number() -> str:
    return f"R{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def issue_receipt(db: Session, sale: Sale, payment: Payment) -> Receipt:
    """Creates the immutable receipt for a completed sale (flush only, caller commits)."""
    return receipt_repository.create(
        db,
        {
            "receipt_number": _new_receipt_number(),
            "sale_id": sale.sale_id,
            "payment_id": payment.payment_id,
            "subtotal": sale.subtotal,
            "discount": sale.discount_total,
            "vat": sale.tax_total,
            "total_amount": sale.total_amount,
            "amount_tendered": payment.amount_tendered,
            "change_due": payment.change_due,
            "prices_include_tax": sale.prices_include_tax,
        },
    )


def _assert_can_view(db: Session, receipt: Receipt, user: User) -> None:
    if user.role in (UserRole.ADMIN.value, UserRole.MANAGER.value):
        return
    sale = sale_repository.get(db, receipt.sale_id)
    if sale is None or sale.cashier_id != user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")


def get_receipt(db: Session, receipt_id: uuid.UUID, user: User) -> Receipt:
    receipt = get_or_404(receipt_repository, db, receipt_id, "Receipt")
    _assert_can_view(db, receipt, user)
    return receipt


def get_receipt_for_sale(db: Session, sale_id: uuid.UUID, user: User) -> Receipt:
    receipt = receipt_repository.get_by_sale_id(db, sale_id)
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    _assert_can_view(db, receipt, user)
    return receipt


def list_receipts(db: Session, *, skip: int = 0, limit: int = 100):
    return receipt_repository.get_all(db, skip=skip, limit=limit)


receipt_service = SimpleNamespace(
    get_receipt=get_receipt,
    get_receipt_for_sale=get_receipt_for_sale,
    list_receipts=list_receipts,
)
