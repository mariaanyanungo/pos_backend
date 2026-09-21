import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "pytest-only-secret-key-0123456789-abcdefghijklmnop"
os.environ["PRICES_INCLUDE_TAX"] = "false"
for _name in ("BOOTSTRAP_ADMIN_USERNAME", "BOOTSTRAP_ADMIN_EMAIL", "BOOTSTRAP_ADMIN_PASSWORD"):
    os.environ.pop(_name, None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import UserRole
from app.core.security import create_access_token, hash_password
from app.models.user import User
from database import Base, get_db
from main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

PASSWORD = "testpassword"


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(client):
    """A raw session on the same test database (for seeding / asserting directly)."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_user(db, username: str, role: UserRole, *, is_active: bool = True) -> User:
    user = User(
        username=username,
        email=f"{username}@pos.com",
        hashed_password=hash_password(PASSWORD),
        title=role.value.title(),
        role=role.value,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def bearer(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id)}"}


@pytest.fixture
def test_user(client):
    """A cashier created through the public registration endpoint."""
    test_user_data = {
        "username": "testuser",
        "email": "testuser@gmail.com",
        "password": "testpassword",
    }
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 201, response.text
    return test_user_data


@pytest.fixture
def auth_headers(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]},
    )
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_user(db_session):
    return seed_user(db_session, "admin", UserRole.ADMIN)


@pytest.fixture
def admin_headers(admin_user):
    return bearer(admin_user)


@pytest.fixture
def manager_user(db_session):
    return seed_user(db_session, "manager", UserRole.MANAGER)


@pytest.fixture
def manager_headers(manager_user):
    return bearer(manager_user)


@pytest.fixture
def other_cashier_headers(db_session):
    return bearer(seed_user(db_session, "othercashier", UserRole.CASHIER))


@pytest.fixture
def category(client, admin_headers):
    response = client.post("/categories", json={"name": "Beverages"}, headers=admin_headers)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def make_product(client, admin_headers, category):
    """Factory: make_product(price="10.00", tax_rate="20.00", stock_quantity=10, ...)."""
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        payload = {
            "name": f"Product {counter['n']}",
            "brand_name": "Coco",
            "barcode": f"BARCODE-{counter['n']:04d}",
            "price": "10.00",
            "tax_rate": "20.00",
            "stock_quantity": 10,
            "category_id": category["category_id"],
        }
        payload.update(overrides)
        response = client.post("/products", json=payload, headers=admin_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make



class PosApi:
    """Thin helper around the till workflow, bound to one set of credentials."""

    def __init__(self, client, headers):
        self.client = client
        self.headers = headers
        self._keys = 0

    def new_sale(self, headers=None, **body):
        response = self.client.post("/sales", json=body, headers=headers or self.headers)
        assert response.status_code == 201, response.text
        return response.json()

    def add_item(self, sale_id, product_id, quantity=1, headers=None, **extra):
        response = self.client.post(
            f"/sales/{sale_id}/items",
            json={"product_id": product_id, "quantity": quantity, **extra},
            headers=headers or self.headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    def get_sale(self, sale_id, headers=None):
        response = self.client.get(f"/sales/{sale_id}", headers=headers or self.headers)
        assert response.status_code == 200, response.text
        return response.json()

    def checkout(self, sale_id, method="cash", tendered=None, key=None, headers=None):
        if key is None:
            self._keys += 1
            key = f"key-{sale_id}-{self._keys}"
        body = {"payment_method": method}
        if tendered is not None:
            body["amount_tendered"] = tendered
        return self.client.post(
            f"/sales/{sale_id}/checkout",
            json=body,
            headers={**(headers or self.headers), "Idempotency-Key": key},
        )

    def completed_sale(self, product_id, quantity=1, **item_extra):
        """Open a sale, add one product line and pay it in cash. Returns the checkout body."""
        sale = self.new_sale()
        self.add_item(sale["sale_id"], product_id, quantity, **item_extra)
        cart = self.get_sale(sale["sale_id"])
        response = self.checkout(sale["sale_id"], "cash", tendered=str(cart["total_amount"]))
        assert response.status_code == 201, response.text
        return response.json()


@pytest.fixture
def pos(client, auth_headers):
    return PosApi(client, auth_headers)


def get_stock(client, headers, product_id) -> int:
    response = client.get(f"/products/{product_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["stock_quantity"]