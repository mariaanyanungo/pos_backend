import uuid
from decimal import Decimal

import pytest


def product_payload(category, supplier, **overrides):
    payload = {
        "name": "Cocacola",
        "brand_name": "Coco",
        "barcode": "5449000000996",
        "price": "2.50",
        "tax_rate": "0.20",
        "stock_quantity": 40,
        "category_id": category["category_id"],
        "supplier_id": supplier["supplier_id"],
    }
    payload.update(overrides)
    return payload


def test_list_products_empty(client, auth_headers):
    response = client.get("/products", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_products(client, auth_headers, product_factory):
    first = product_factory(name="Cocacola")
    second = product_factory(name="Fanta")
    response = client.get("/products", headers=auth_headers)
    assert response.status_code == 200
    ids = [p["product_id"] for p in response.json()]
    assert ids == [first["product_id"], second["product_id"]]


def test_list_products_is_ordered_by_name(client, auth_headers, product_factory):
    product_factory(name="Zebra Cakes")
    product_factory(name="Apple Juice")
    product_factory(name="Milk")
    response = client.get("/products", headers=auth_headers)
    names = [p["name"] for p in response.json()]
    assert names == ["Apple Juice", "Milk", "Zebra Cakes"]


def test_list_products_pagination(client, auth_headers, product_factory):
    for name in ["Apple", "Banana", "Cherry"]:
        product_factory(name=name)

    first_page = client.get("/products?limit=2", headers=auth_headers).json()
    second_page = client.get("/products?skip=2&limit=2", headers=auth_headers).json()

    assert [p["name"] for p in first_page] == ["Apple", "Banana"]
    assert [p["name"] for p in second_page] == ["Cherry"]


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "skip=-1"])
def test_list_products_with_invalid_pagination_returns_422(client, auth_headers, query):
    response = client.get(f"/products?{query}", headers=auth_headers)
    assert response.status_code == 422


def test_filter_products_by_category(client, auth_headers, category, product_factory):
    other_category = client.post(
        "/categories", json={"name": "Snacks"}, headers=auth_headers
    ).json()
    in_category = product_factory(name="Cola")
    product_factory(name="Chips", category_id=other_category["category_id"])

    response = client.get(
        f"/products?category_id={category['category_id']}", headers=auth_headers
    )
    assert [p["product_id"] for p in response.json()] == [in_category["product_id"]]


def test_filter_products_by_supplier(client, auth_headers, product_factory):
    other_supplier = client.post(
        "/suppliers",
        json={
            "name": "Other Supplier",
            "email": "other@example.com",
            "phone": "+37062222222",
            "address": "2 Side Street",
        },
        headers=auth_headers,
    ).json()
    product_factory(name="Cola")
    from_other = product_factory(name="Chips", supplier_id=other_supplier["supplier_id"])

    response = client.get(
        f"/products?supplier_id={other_supplier['supplier_id']}", headers=auth_headers
    )
    assert [p["product_id"] for p in response.json()] == [from_other["product_id"]]


def test_filter_products_by_barcode(client, auth_headers, product_factory):
    product_factory(name="Cola", barcode="1111111111111")
    target = product_factory(name="Chips", barcode="2222222222222")

    response = client.get("/products?barcode=2222222222222", headers=auth_headers)
    assert [p["product_id"] for p in response.json()] == [target["product_id"]]


def test_search_products_by_name_is_case_insensitive(client, auth_headers, product_factory):
    match = product_factory(name="Cocacola Zero")
    product_factory(name="Fanta Orange")

    response = client.get("/products?search=COLA", headers=auth_headers)
    assert [p["product_id"] for p in response.json()] == [match["product_id"]]


def test_search_products_by_barcode(client, auth_headers, product_factory):
    match = product_factory(name="Cola", barcode="9876543210123")
    product_factory(name="Chips", barcode="1111111111111")

    response = client.get("/products?search=98765432", headers=auth_headers)
    assert [p["product_id"] for p in response.json()] == [match["product_id"]]



def test_create_product(client, auth_headers, category, supplier):
    product_data = product_payload(category, supplier)
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["product_id"])
    assert body["name"] == "Cocacola"
    assert body["brand_name"] == "Coco"
    assert body["barcode"] == "5449000000996"
    assert Decimal(body["price"]) == Decimal("2.50")
    assert Decimal(body["tax_rate"]) == Decimal("0.20")
    assert body["stock_quantity"] == 40
    assert body["category_id"] == category["category_id"]
    assert body["supplier_id"] == supplier["supplier_id"]
    assert body["is_active"] is True
    assert "created_at" in body


def test_create_product_applies_defaults(client, auth_headers, category):
    product_data = {
        "name": "Water",
        "brand_name": "Aqua",
        "barcode": "0000000000001",
        "price": "1.00",
        "category_id": category["category_id"],
    }
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["tax_rate"]) == Decimal("0")
    assert body["stock_quantity"] == 0
    assert body["supplier_id"] is None


def test_create_product_stores_exact_price(client, auth_headers, category, supplier):
    product_data = product_payload(category, supplier, price="19.99")
    created = client.post("/products", json=product_data, headers=auth_headers).json()
    fetched = client.get(f"/products/{created['product_id']}", headers=auth_headers).json()
    assert Decimal(fetched["price"]) == Decimal("19.99")


@pytest.mark.parametrize(
    "missing_field", ["name", "brand_name", "barcode", "price", "category_id"]
)
def test_create_product_missing_required_field_returns_422(
    client, auth_headers, category, supplier, missing_field
):
    product_data = product_payload(category, supplier)
    product_data.pop(missing_field)
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"barcode": ""},
        {"price": "-1.00"},
        {"price": "10.999"},
        {"price": "abc"},
        {"tax_rate": "-0.01"},
        {"tax_rate": "1.01"},
        {"stock_quantity": -1},
    ],
)
def test_create_product_with_invalid_data_returns_422(
    client, auth_headers, category, supplier, overrides
):
    product_data = product_payload(category, supplier, **overrides)
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 422


def test_create_product_with_duplicate_barcode_returns_409(
    client, auth_headers, category, supplier, product_factory
):
    product_factory(barcode="DUP001")
    product_data = product_payload(category, supplier, barcode="DUP001")
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 409


def test_create_product_with_unknown_category_returns_404(
    client, auth_headers, category, supplier
):
    product_data = product_payload(
        category, supplier, category_id=str(uuid.uuid4())
    )
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 404


def test_create_product_with_unknown_supplier_returns_404(
    client, auth_headers, category, supplier
):
    product_data = product_payload(
        category, supplier, supplier_id=str(uuid.uuid4())
    )
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 404


def test_create_product_without_login_returns_401(client, category, supplier):
    product_data = product_payload(category, supplier)
    response = client.post("/products", json=product_data)
    assert response.status_code == 401


def test_create_product_with_invalid_token_returns_401(client, category, supplier):
    product_data = product_payload(category, supplier)
    response = client.post(
        "/products",
        json=product_data,
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == 401


def test_get_product(client, auth_headers, product):
    response = client.get(f"/products/{product['product_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == product


def test_get_nonexistent_product_returns_404(client, auth_headers):
    response = client.get(f"/products/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_product_with_malformed_id_returns_422(client, auth_headers):
    response = client.get("/products/10000", headers=auth_headers)
    assert response.status_code == 422


def test_update_product(client, auth_headers, product):
    updated_product = {"name": "Fanta", "price": "3.75"}
    response = client.put(
        f"/products/{product['product_id']}",
        json=updated_product,
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Fanta"
    assert Decimal(body["price"]) == Decimal("3.75")
    assert body["barcode"] == product["barcode"]
    assert body["brand_name"] == product["brand_name"]

    persisted = client.get(f"/products/{product['product_id']}", headers=auth_headers)
    assert persisted.json()["name"] == "Fanta"


def test_update_product_with_empty_body_changes_nothing(client, auth_headers, product):
    response = client.put(
        f"/products/{product['product_id']}", json={}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == product


def test_update_product_to_duplicate_barcode_returns_409(
    client, auth_headers, product_factory
):
    product_factory(barcode="TAKEN001")
    other = product_factory(barcode="FREE001")
    response = client.put(
        f"/products/{other['product_id']}",
        json={"barcode": "TAKEN001"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_update_product_keeping_its_own_barcode_returns_200(client, auth_headers, product):
    response = client.put(
        f"/products/{product['product_id']}",
        json={"barcode": product["barcode"], "name": "Renamed"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_update_product_cannot_change_stock_directly(
    client, auth_headers, product, get_stock
):
    response = client.put(
        f"/products/{product['product_id']}",
        json={"stock_quantity": 5},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert get_stock(product["product_id"]) == 100


@pytest.mark.parametrize(
    "overrides",
    [{"price": "-5.00"}, {"tax_rate": "2"}, {"name": ""}, {"price": "1.234"}],
)
def test_update_product_with_invalid_data_returns_422(
    client, auth_headers, product, overrides
):
    response = client.put(
        f"/products/{product['product_id']}", json=overrides, headers=auth_headers
    )
    assert response.status_code == 422


def test_update_product_with_unknown_category_returns_404(client, auth_headers, product):
    response = client.put(
        f"/products/{product['product_id']}",
        json={"category_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_nonexistent_product_returns_404(client, auth_headers):
    response = client.put(
        f"/products/{uuid.uuid4()}", json={"name": "Ghost"}, headers=auth_headers
    )
    assert response.status_code == 404


# ---------- delete ----------

def test_delete_product(client, auth_headers, product):
    response = client.delete(f"/products/{product['product_id']}", headers=auth_headers)
    assert response.status_code == 204
    assert response.content == b""


def test_deleted_product_is_hidden_from_default_list(client, auth_headers, product):
    client.delete(f"/products/{product['product_id']}", headers=auth_headers)

    default_list = client.get("/products", headers=auth_headers).json()
    assert default_list == []

    inactive_list = client.get("/products?is_active=false", headers=auth_headers).json()
    assert [p["product_id"] for p in inactive_list] == [product["product_id"]]


def test_deleted_product_can_still_be_fetched_as_inactive(client, auth_headers, product):
    client.delete(f"/products/{product['product_id']}", headers=auth_headers)
    response = client.get(f"/products/{product['product_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_deleted_product_barcode_cannot_be_reused(
    client, auth_headers, category, supplier, product
):
    client.delete(f"/products/{product['product_id']}", headers=auth_headers)
    product_data = product_payload(category, supplier, barcode=product["barcode"])
    response = client.post("/products", json=product_data, headers=auth_headers)
    assert response.status_code == 409


def test_delete_nonexistent_product_returns_404(client, auth_headers):
    response = client.delete(f"/products/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404