import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import StockReason
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User
from app.repositories.inventory_movement import inventory_movement_repository
from app.repositories.product import product_repository
from app.services.common import get_or_404


def deduct_for_sale(db: Session, sale: Sale, user: User) -> None:
    """Takes stock for every line of the sale, atomically per product.

    Lines are processed in a stable (product id) order so two concurrent
    checkouts touching the same products cannot deadlock each other. Raises 409
    if any line cannot be fulfilled; the caller must roll the transaction back.
    """
    for item in sorted(sale.items, key=lambda line: str(line.product_id)):
        taken = product_repository.adjust_stock(db, item.product_id, -item.quantity, require_active=True)
        if not taken:
            product = product_repository.get(db, item.product_id)
            if product is not None:
                db.refresh(product)
            if product is None or not product.is_active:
                raise HTTPException(status.HTTP_409_CONFLICT, detail=f"'{item.product_name}' is no longer available")
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=(
                    f"Insufficient stock for '{item.product_name}': "
                    f"requested {item.quantity}, available {product.stock_quantity}"
                ),
            )
        inventory_movement_repository.record(
            db,
            product_id=item.product_id,
            quantity_change=-item.quantity,
            reason=StockReason.SALE.value,
            sale_id=sale.sale_id,
            user_id=user.user_id,
        )


def restore_stock(
    db: Session,
    product_id: uuid.UUID,
    quantity: int,
    reason: StockReason,
    *,
    sale_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> None:
    """Puts returned/voided units back on the shelf and logs it."""
    product_repository.adjust_stock(db, product_id, quantity)
    inventory_movement_repository.record(
        db,
        product_id=product_id,
        quantity_change=quantity,
        reason=reason.value,
        sale_id=sale_id,
        user_id=user_id,
    )


def record_initial_stock(db: Session, product: Product, user: User | None) -> None:
    if product.stock_quantity > 0:
        inventory_movement_repository.record(
            db,
            product_id=product.product_id,
            quantity_change=product.stock_quantity,
            reason=StockReason.INITIAL.value,
            user_id=user.user_id if user else None,
        )


def manual_adjustment(
    db: Session,
    product_id: uuid.UUID,
    quantity_change: int,
    reason: str,
    note: str | None,
    user: User,
) -> Product:
    product = get_or_404(product_repository, db, product_id, "Product")
    if not product_repository.adjust_stock(db, product_id, quantity_change):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Adjustment would make stock negative")
    inventory_movement_repository.record(
        db,
        product_id=product_id,
        quantity_change=quantity_change,
        reason=reason,
        user_id=user.user_id,
        note=note,
    )
    db.commit()
    db.refresh(product)
    return product


def list_movements(db: Session, product_id: uuid.UUID, *, skip: int = 0, limit: int = 100):
    get_or_404(product_repository, db, product_id, "Product")
    return inventory_movement_repository.list_for_product(db, product_id, skip=skip, limit=limit)