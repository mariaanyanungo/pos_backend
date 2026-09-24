import uuid
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.category import category_repository
from app.repositories.product import product_repository
from app.repositories.supplier import supplier_repository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services import inventory as inventory_service
from app.services.common import conflict_on_integrity_error, get_or_404


def get_product(db: Session, product_id: uuid.UUID):
    return get_or_404(product_repository, db, product_id, "Product")


def get_product_by_barcode(db: Session, barcode: str):
    product = product_repository.get_by_barcode(db, barcode.strip())
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def list_products(
    db: Session,
    *,
    category_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    brand_name: str | None = None,
    name: str | None = None,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = 100,
):
    return product_repository.search(
        db,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
        filters={
            "category_id": category_id,
            "supplier_id": supplier_id,
            "brand_name": brand_name,
        },
        name_contains=name,
    )


def _validate_references(
    db: Session, category_id: uuid.UUID | None, supplier_id: uuid.UUID | None
) -> None:
    if category_id is not None:
        category = category_repository.get(db, category_id)
        if category is None or not category.is_active:
            raise HTTPException(422, detail="category_id does not exist or is inactive")
    if supplier_id is not None:
        supplier = supplier_repository.get(db, supplier_id)
        if supplier is None or not supplier.is_active:
            raise HTTPException(422, detail="supplier_id does not exist or is inactive")


def create_product(db: Session, data: ProductCreate, user: User | None = None):
    _validate_references(db, data.category_id, data.supplier_id)
    with conflict_on_integrity_error(db, "A product with this barcode already exists"):
        product = product_repository.create(db, data.model_dump())
        inventory_service.record_initial_stock(db, product, user)
        db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: uuid.UUID, data: ProductUpdate):
    product = get_product(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    _validate_references(db, changes.get("category_id"), changes.get("supplier_id"))
    with conflict_on_integrity_error(db, "A product with this barcode already exists"):
        product_repository.update(db, product, changes)
        db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: uuid.UUID) -> None:
    """Soft delete: sale history keeps referencing the product."""
    product = get_product(db, product_id)
    product_repository.update(db, product, {"is_active": False})
    db.commit()


product_service = SimpleNamespace(
    get_product=get_product,
    get_product_by_barcode=get_product_by_barcode,
    list_products=list_products,
    create_product=create_product,
    update_product=update_product,
    delete_product=delete_product,
)
