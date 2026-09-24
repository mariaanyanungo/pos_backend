import uuid
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import SaleStatus
from app.core.money import ZERO
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User
from app.repositories.product import product_repository
from app.schemas.sale_item import SaleItemCreate, SaleItemUpdate
from app.services import sale as sale_svc

_CLOSED_MESSAGE = "Items can only be changed while the sale is open"


def _resolve_product(db: Session, data: SaleItemCreate) -> Product:
    if data.product_id is not None:
        product = product_repository.get(db, data.product_id)
    else:
        product = product_repository.get_by_barcode(db, data.barcode.strip())
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not product.is_active:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"'{product.name}' is not available for sale",
        )
    return product


def _check_stock(product: Product, wanted: int) -> None:
    # Friendly early warning only. The authoritative, race-free check is the
    # atomic stock deduction at checkout.
    if product.stock_quantity < wanted:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Insufficient stock for '{product.name}': requested {wanted}, available {product.stock_quantity}",
        )


def add_item(db: Session, sale_id: uuid.UUID, data: SaleItemCreate, user: User) -> Sale:
    sale = sale_svc.get_sale(db, sale_id, user, for_update=True)
    sale_svc.require_status(sale, SaleStatus.OPEN, _CLOSED_MESSAGE)
    product = _resolve_product(db, data)

    existing = next(
        (line for line in sale.items if line.product_id == product.product_id), None
    )
    wanted = data.quantity + (existing.quantity if existing else 0)
    _check_stock(product, wanted)

    discount_given = (
        data.discount_amount is not None or data.discount_percent is not None
    )
    if existing is not None:
        existing.quantity = wanted
        if discount_given:
            existing.discount_percent = data.discount_percent
            existing.discount_amount = (
                data.discount_amount if data.discount_amount is not None else ZERO
            )
    else:
        sale.items.append(
            SaleItem(
                product_id=product.product_id,
                product_name=product.name,
                barcode=product.barcode,
                unit_price=product.price,
                tax_rate=product.tax_rate,
                quantity=data.quantity,
                discount_percent=data.discount_percent,
                discount_amount=data.discount_amount
                if data.discount_amount is not None
                else ZERO,
            )
        )

    sale_svc.reprice(sale)
    db.commit()
    db.refresh(sale)
    return sale


def update_item(
    db: Session,
    sale_id: uuid.UUID,
    item_id: uuid.UUID,
    data: SaleItemUpdate,
    user: User,
) -> Sale:
    sale = sale_svc.get_sale(db, sale_id, user, for_update=True)
    sale_svc.require_status(sale, SaleStatus.OPEN, _CLOSED_MESSAGE)
    item = _find_item(sale, item_id)
    provided = data.model_fields_set

    if "quantity" in provided and data.quantity is not None:
        product = product_repository.get(db, item.product_id)
        if product is not None:
            _check_stock(product, data.quantity)
        item.quantity = data.quantity

    if "discount_amount" in provided or "discount_percent" in provided:
        item.discount_percent = data.discount_percent
        item.discount_amount = (
            data.discount_amount if data.discount_amount is not None else ZERO
        )

    sale_svc.reprice(sale)
    db.commit()
    db.refresh(sale)
    return sale


def remove_item(
    db: Session, sale_id: uuid.UUID, item_id: uuid.UUID, user: User
) -> Sale:
    sale = sale_svc.get_sale(db, sale_id, user, for_update=True)
    sale_svc.require_status(sale, SaleStatus.OPEN, _CLOSED_MESSAGE)
    item = _find_item(sale, item_id)
    sale.items.remove(item)  # delete-orphan removes the row
    sale_svc.reprice(sale)
    db.commit()
    db.refresh(sale)
    return sale


def _find_item(sale: Sale, item_id: uuid.UUID) -> SaleItem:
    item = next((line for line in sale.items if line.sale_item_id == item_id), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sale item not found")
    return item


sale_item_service = SimpleNamespace(
    add_item=add_item,
    update_item=update_item,
    remove_item=remove_item,
)
