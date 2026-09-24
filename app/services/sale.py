import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import SaleStatus, StockReason, UserRole
from app.core.money import ZERO, money
from app.models.sale import Sale
from app.models.user import User
from app.repositories.customer import customer_repository
from app.repositories.payment import payment_repository
from app.repositories.sale import sale_repository
from app.schemas.sale import RefundRequest, SaleCreate
from app.services import inventory as inventory_svc
from app.services import payment as payment_svc
from app.services import pricing

PRIVILEGED_ROLES = {UserRole.ADMIN.value, UserRole.MANAGER.value}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_privileged(user: User) -> bool:
    return user.role in PRIVILEGED_ROLES


def require_privileged(user: User, action: str) -> None:
    if not is_privileged(user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"Manager or admin approval is required to {action}",
        )


def assert_access(sale: Sale, user: User) -> None:
    # Cashiers only ever see their own sales; a foreign id looks like "not found".
    if not is_privileged(user) and sale.cashier_id != user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sale not found")


def require_status(sale: Sale, expected: SaleStatus, message: str) -> None:
    if sale.status != expected.value:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=message)


def reprice(sale: Sale) -> None:
    """Recalculate line and sale totals; pricing violations become HTTP 422."""
    try:
        pricing.recalculate_sale(sale)
    except pricing.PricingError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


def get_sale(
    db: Session, sale_id: uuid.UUID, user: User, *, for_update: bool = False
) -> Sale:
    sale = (
        sale_repository.get_for_update(db, sale_id)
        if for_update
        else sale_repository.get_with_items(db, sale_id)
    )
    if sale is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sale not found")
    assert_access(sale, user)
    return sale


def list_sales(
    db: Session,
    user: User,
    *,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    cashier_id = None if is_privileged(user) else user.user_id
    return sale_repository.search(
        db, cashier_id=cashier_id, status=status_filter, skip=skip, limit=limit
    )


def create_sale(db: Session, data: SaleCreate, user: User) -> Sale:
    if data.customer_id is not None:
        customer = customer_repository.get(db, data.customer_id)
        if customer is None or not customer.is_active:
            raise HTTPException(422, detail="customer_id does not exist or is inactive")
    sale = sale_repository.create(
        db,
        {
            "customer_id": data.customer_id,
            "cashier_id": user.user_id,
            "status": SaleStatus.OPEN.value,
            "prices_include_tax": settings.prices_include_tax,
        },
    )
    db.commit()
    db.refresh(sale)
    return sale


def void_sale(db: Session, sale_id: uuid.UUID, reason: str | None, user: User) -> Sale:
    """Cancel a sale.

    * open cart      -> voided, nothing else to undo (no stock was taken, no money moved)
    * completed sale -> manager/admin only: every remaining unit goes back to stock and the
                        remaining captured amount is refunded, then the sale is voided
    """
    sale = get_sale(db, sale_id, user, for_update=True)
    try:
        if sale.status == SaleStatus.OPEN.value:
            pass
        elif sale.status == SaleStatus.COMPLETED.value:
            require_privileged(user, "void a completed sale")
            payment = payment_repository.get_captured_for_sale(db, sale.sale_id)
            if payment is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Sale has no captured payment to reverse",
                )
            lines = [
                (item, item.quantity - item.returned_quantity) for item in sale.items
            ]
            lines = [(item, units) for item, units in lines if units > 0]
            _return_lines(db, sale, payment, lines, user, stock_reason=StockReason.VOID)
        else:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail=f"Sale is already {sale.status}"
            )

        sale.status = SaleStatus.VOIDED.value
        sale.voided_at = _now()
        sale.void_reason = reason
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sale)
    return sale


def refund_sale(db: Session, sale_id: uuid.UUID, data: RefundRequest, user: User):
    """Return some or all units of a completed sale (manager/admin)."""
    require_privileged(user, "refund a sale")
    sale = get_sale(db, sale_id, user, for_update=True)
    try:
        require_status(
            sale, SaleStatus.COMPLETED, "Only completed sales can be refunded"
        )
        payment = payment_repository.get_captured_for_sale(db, sale.sale_id)
        if payment is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Sale has no captured payment to refund",
            )

        items = {item.sale_item_id: item for item in sale.items}
        requested: dict[uuid.UUID, int] = {}
        for line in data.items:
            requested[line.sale_item_id] = (
                requested.get(line.sale_item_id, 0) + line.quantity
            )

        lines = []
        for item_id, units in requested.items():
            item = items.get(item_id)
            if item is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, detail="Sale item not found on this sale"
                )
            returnable = item.quantity - item.returned_quantity
            if units > returnable:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail=f"Cannot return {units} of '{item.product_name}': only {returnable} left to return",
                )
            lines.append((item, units))

        refund_total = _return_lines(
            db, sale, payment, lines, user, stock_reason=StockReason.RETURN
        )
        if all(item.returned_quantity == item.quantity for item in sale.items):
            sale.status = SaleStatus.REFUNDED.value
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sale)
    db.refresh(payment)
    return sale, payment, refund_total


def _return_lines(
    db: Session, sale: Sale, payment, lines, user: User, *, stock_reason: StockReason
):
    """Shared by void and refund: restock units, book the refund on each line and
    on the payment. Runs inside the caller's transaction."""
    refund_total = ZERO
    for item, units in lines:
        amount = pricing.refund_amount_for_units(
            line_total=item.line_total,
            quantity=item.quantity,
            units_already_returned=item.returned_quantity,
            amount_already_refunded=item.refunded_total,
            units=units,
        )
        item.returned_quantity += units
        item.refunded_total = money(item.refunded_total + amount)
        refund_total += amount
        inventory_svc.restore_stock(
            db,
            item.product_id,
            units,
            stock_reason,
            sale_id=sale.sale_id,
            user_id=user.user_id,
        )
    refund_total = money(refund_total)
    payment_svc.refund(payment, refund_total)
    db.flush()
    return refund_total


sale_service = SimpleNamespace(
    get_sale=get_sale,
    list_sales=list_sales,
    create_sale=create_sale,
    void_sale=void_sale,
    refund_sale=refund_sale,
)
