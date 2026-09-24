import uuid

from app.core.enums import UserRole
from app.repositories.category import category_repository
from app.repositories.product import product_repository
from app.repositories.user import user_repository

from .conftest import seed_user


def _make_product(db, *, stock=5, active=True):
    category = category_repository.create(db, {"name": f"cat-{uuid.uuid4().hex[:6]}"})
    product = product_repository.create(
        db,
        {
            "name": "Widget",
            "brand_name": "Acme",
            "price": "2.00",
            "category_id": category.category_id,
            "stock_quantity": stock,
            "is_active": active,
        },
    )
    db.commit()
    return product


def test_adjust_stock_decrements_when_enough(db_session):
    product = _make_product(db_session, stock=5)
    assert product_repository.adjust_stock(db_session, product.product_id, -3) is True
    db_session.commit()
    db_session.refresh(product)
    assert product.stock_quantity == 2


def test_adjust_stock_refuses_to_go_negative_and_changes_nothing(db_session):
    product = _make_product(db_session, stock=2)
    assert product_repository.adjust_stock(db_session, product.product_id, -3) is False
    db_session.commit()
    db_session.refresh(product)
    assert product.stock_quantity == 2


def test_adjust_stock_can_take_exactly_the_last_unit(db_session):
    product = _make_product(db_session, stock=1)
    assert product_repository.adjust_stock(db_session, product.product_id, -1) is True
    assert product_repository.adjust_stock(db_session, product.product_id, -1) is False


def test_adjust_stock_require_active(db_session):
    product = _make_product(db_session, stock=5, active=False)
    assert (
        product_repository.adjust_stock(
            db_session, product.product_id, -1, require_active=True
        )
        is False
    )
    assert (
        product_repository.adjust_stock(db_session, product.product_id, 4) is True
    )  # restocking is allowed


def test_adjust_stock_unknown_product_returns_false(db_session):
    assert product_repository.adjust_stock(db_session, uuid.uuid4(), 1) is False


def test_update_applies_every_field_not_just_the_first(db_session):
    product = _make_product(db_session)
    product_repository.update(
        db_session, product, {"name": "Gadget", "brand_name": "Globex"}
    )
    db_session.commit()
    db_session.refresh(product)
    assert (product.name, product.brand_name) == ("Gadget", "Globex")


def test_get_all_hides_inactive_by_default(db_session):
    _make_product(db_session, active=True)
    _make_product(db_session, active=False)
    assert len(product_repository.get_all(db_session)) == 1
    assert len(product_repository.get_all(db_session, include_inactive=True)) == 2


def test_user_lookup_by_username_uses_the_username_column(db_session):
    user = seed_user(db_session, "cashier1", UserRole.CASHIER)
    assert (
        user_repository.get_by_username(db_session, "cashier1").user_id == user.user_id
    )
    assert user_repository.get_by_username(db_session, str(user.user_id)) is None
    assert user_repository.get_by_id(db_session, user.user_id).username == "cashier1"
    assert user_repository.count(db_session) == 1
