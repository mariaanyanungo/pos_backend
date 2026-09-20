import itertools
import os
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-at-least-32-chars-long"

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autoflush=False, bind=engine)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(client):
    """Direct DB access for assertions. Call db_session.expire_all() before
    re-reading rows that the API changed."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(client):
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
        data={
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )
    assert response.status_code == 200, response.text
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def category(client, auth_headers):
    response = client.post(
        "/categories", json={"name": "Beverages"}, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def supplier(client, auth_headers):
    response = client.post(
        "/suppliers",
        json={
            "name": "Acme Distributors",
            "email": "acme@example.com",
            "phone": "+37060000000",
            "address": "1 Main Street",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def customer(client, auth_headers):
    response = client.post(
        "/customers",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+37061111111",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def product_factory(client, auth_headers, category, supplier):
    counter = itertools.count(1)

    def _create(**overrides):
        n = next(counter)
        payload = {
            "name": f"Product {n}",
            "brand_name": "Coco",
            "barcode": f"BC{n:010d}",
            "price": "10.00",
            "tax_rate": "0.20",
            "stock_quantity": 100,
            "category_id": category["category_id"],
            "supplier_id": supplier["supplier_id"],
        }
        payload.update(overrides)
        response = client.post("/products", json=payload, headers=auth_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def product(product_factory):
    return product_factory()


@pytest.fixture
def get_stock(client, auth_headers):
    def _get_stock(product_id):
        response = client.get(f"/products/{product_id}", headers=auth_headers)
        assert response.status_code == 200, response.text
        return response.json()["stock_quantity"]

    return _get_stock


@pytest.fixture
def checkout(client, auth_headers):
    """Returns the raw response so tests can assert on failures too.

    items: [{"product_id": "...", "quantity": 2, "discount": "0.00"}]
    """

    def _checkout(items, payment=None, customer_id=None, idempotency_key=None):
        body = {
            "items": items,
            "payment": payment or {"method": "cash", "amount_tendered": "1000.00"},
        }
        if customer_id:
            body["customer_id"] = str(customer_id)
        headers = {
            **auth_headers,
            "Idempotency-Key": idempotency_key or str(uuid.uuid4()),
        }
        return client.post("/sales/checkout", json=body, headers=headers)

    return _checkout