from .conftest import get_stock


def _payload(category, **overrides):
    payload = {
        "name": "Cocacola",
        "brand_name": "Coco",
        "barcode": "5449000000996",
        "price": "1.50",
        "tax_rate": "21.00",
        "category_id": category["category_id"],
        "stock_quantity": 24,
    }
    payload.update(overrides)
    return payload


def test_list_products(client, auth_headers):
    response = client.get("/products", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_products_without_login_returns_401(client):
    assert client.get("/products").status_code == 401


def test_create_product(client, admin_headers, category):
    response = client.post("/products", json=_payload(category), headers=admin_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Cocacola"
    assert body["price"] == "1.50"
    assert body["tax_rate"] == "21.00"
    assert body["stock_quantity"] == 24
    assert body["is_active"] is True
    assert "product_id" in body and "created_at" in body


def test_create_product_without_login_returns_401(client, category):
    response = client.post("/products", json=_payload(category))
    assert response.status_code == 401


def test_cashier_cannot_create_update_or_delete_products(
    client, auth_headers, make_product, category
):
    product = make_product()
    assert (
        client.post(
            "/products", json=_payload(category), headers=auth_headers
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/products/{product['product_id']}",
            json={"name": "X"},
            headers=auth_headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/products/{product['product_id']}", headers=auth_headers
        ).status_code
        == 403
    )


def test_create_product_without_name_returns_422(client, admin_headers, category):
    body = _payload(category)
    del body["name"]
    assert client.post("/products", json=body, headers=admin_headers).status_code == 422


def test_create_product_with_invalid_values_returns_422(
    client, admin_headers, category
):
    for bad in (
        {"price": "-1.00"},
        {"price": "1.005"},
        {"tax_rate": "101"},
        {"tax_rate": "-1"},
        {"stock_quantity": -5},
        {"price": "abc"},
    ):
        response = client.post(
            "/products", json=_payload(category, **bad), headers=admin_headers
        )
        assert response.status_code == 422, bad


def test_create_product_with_unknown_category_returns_422(
    client, admin_headers, category
):
    body = _payload(category, category_id="00000000-0000-0000-0000-000000000000")
    assert client.post("/products", json=body, headers=admin_headers).status_code == 422


def test_create_product_with_unknown_supplier_returns_422(
    client, admin_headers, category
):
    body = _payload(category, supplier_id="00000000-0000-0000-0000-000000000000")
    assert client.post("/products", json=body, headers=admin_headers).status_code == 422


def test_create_product_with_supplier(client, admin_headers, category):
    supplier = client.post(
        "/suppliers",
        json={
            "name": "Acme",
            "email": "acme@acme.com",
            "phone": "12345",
            "address": "Somewhere 1",
        },
        headers=admin_headers,
    ).json()
    body = _payload(category, supplier_id=supplier["supplier_id"])
    response = client.post("/products", json=body, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["supplier_id"] == supplier["supplier_id"]


def test_duplicate_barcode_returns_409(client, admin_headers, category):
    client.post("/products", json=_payload(category), headers=admin_headers)
    response = client.post(
        "/products", json=_payload(category, name="Other"), headers=admin_headers
    )
    assert response.status_code == 409


def test_blank_barcode_is_stored_as_null_so_many_products_can_omit_it(
    client, admin_headers, category
):
    first = client.post(
        "/products", json=_payload(category, barcode="  "), headers=admin_headers
    )
    second = client.post(
        "/products",
        json=_payload(category, name="Second", barcode=""),
        headers=admin_headers,
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["barcode"] is None


def test_get_product(client, auth_headers, make_product):
    product = make_product()
    response = client.get(f"/products/{product['product_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["product_id"] == product["product_id"]


def test_get_nonexistent_product(client, auth_headers):
    response = client.get(
        "/products/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == 404


def test_get_product_with_malformed_id_returns_422(client, auth_headers):
    assert client.get("/products/10000", headers=auth_headers).status_code == 422


def test_get_product_by_barcode(client, auth_headers, make_product):
    product = make_product(barcode="8590001112223")
    response = client.get("/products/barcode/8590001112223", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["product_id"] == product["product_id"]
    assert (
        client.get("/products/barcode/unknown", headers=auth_headers).status_code == 404
    )


def test_update_product(client, admin_headers, make_product):
    product = make_product(name="Cocacola", brand_name="Coco")
    response = client.put(
        f"/products/{product['product_id']}",
        json={"name": "Fanta", "price": "2.20"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Fanta"
    assert body["price"] == "2.20"
    assert body["brand_name"] == "Coco"


def test_update_cannot_change_stock_directly(client, admin_headers, make_product):
    product = make_product(stock_quantity=5)
    client.put(
        f"/products/{product['product_id']}",
        json={"stock_quantity": 999},
        headers=admin_headers,
    )
    assert get_stock(client, admin_headers, product["product_id"]) == 5


def test_update_to_duplicate_barcode_returns_409(client, admin_headers, make_product):
    first = make_product(barcode="AAA")
    second = make_product(barcode="BBB")
    response = client.put(
        f"/products/{second['product_id']}",
        json={"barcode": first["barcode"]},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_update_nonexistent_product_returns_404(client, admin_headers):
    response = client.put(
        "/products/00000000-0000-0000-0000-000000000000",
        json={"name": "X"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_product_is_soft(client, admin_headers, auth_headers, make_product):
    product = make_product()
    response = client.delete(
        f"/products/{product['product_id']}", headers=admin_headers
    )
    assert response.status_code == 204
    assert client.get("/products", headers=auth_headers).json() == []
    with_inactive = client.get(
        "/products?include_inactive=true", headers=auth_headers
    ).json()
    assert [p["product_id"] for p in with_inactive] == [product["product_id"]]
    assert with_inactive[0]["is_active"] is False


def test_delete_nonexistent_product_returns_404(client, admin_headers):
    assert (
        client.delete(
            "/products/00000000-0000-0000-0000-000000000000", headers=admin_headers
        ).status_code
        == 404
    )


def test_list_products_filters(
    client, auth_headers, admin_headers, category, make_product
):
    other_category = client.post(
        "/categories", json={"name": "Snacks"}, headers=admin_headers
    ).json()
    cola = make_product(name="Cola Zero", brand_name="Coco")
    make_product(
        name="Crisps", brand_name="Lays", category_id=other_category["category_id"]
    )

    by_category = client.get(
        f"/products?category_id={category['category_id']}", headers=auth_headers
    ).json()
    assert [p["product_id"] for p in by_category] == [cola["product_id"]]
    by_brand = client.get("/products?brand_name=Lays", headers=auth_headers).json()
    assert [p["name"] for p in by_brand] == ["Crisps"]
    by_name = client.get("/products?name=cola", headers=auth_headers).json()
    assert [p["product_id"] for p in by_name] == [cola["product_id"]]
    assert client.get("/products?name=%25", headers=auth_headers).json() == []


def test_initial_stock_is_written_to_the_ledger(client, admin_headers, make_product):
    product = make_product(stock_quantity=12)
    movements = client.get(
        f"/products/{product['product_id']}/stock-movements", headers=admin_headers
    ).json()
    assert [(m["quantity_change"], m["reason"]) for m in movements] == [
        (12, "initial_stock")
    ]


def test_stock_adjustments_update_balance_and_ledger(
    client, admin_headers, make_product
):
    product = make_product(stock_quantity=10)
    pid = product["product_id"]
    restock = client.post(
        f"/products/{pid}/stock-adjustments",
        json={"quantity_change": 15, "reason": "restock", "note": "Delivery #42"},
        headers=admin_headers,
    )
    assert restock.status_code == 200
    assert restock.json()["stock_quantity"] == 25
    damage = client.post(
        f"/products/{pid}/stock-adjustments",
        json={"quantity_change": -3, "reason": "damage"},
        headers=admin_headers,
    )
    assert damage.json()["stock_quantity"] == 22
    ledger = client.get(
        f"/products/{pid}/stock-movements", headers=admin_headers
    ).json()
    assert sorted(m["quantity_change"] for m in ledger) == [-3, 10, 15]
    assert sum(m["quantity_change"] for m in ledger) == get_stock(
        client, admin_headers, pid
    )


def test_stock_cannot_go_negative(client, admin_headers, make_product):
    product = make_product(stock_quantity=2)
    response = client.post(
        f"/products/{product['product_id']}/stock-adjustments",
        json={"quantity_change": -3, "reason": "adjustment"},
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert get_stock(client, admin_headers, product["product_id"]) == 2


def test_invalid_stock_adjustments_return_422(client, admin_headers, make_product):
    pid = make_product()["product_id"]
    url = f"/products/{pid}/stock-adjustments"
    assert (
        client.post(url, json={"quantity_change": 0}, headers=admin_headers).status_code
        == 422
    )
    assert (
        client.post(
            url, json={"quantity_change": 1, "reason": "sale"}, headers=admin_headers
        ).status_code
        == 422
    )


def test_cashier_cannot_adjust_stock_or_read_ledger(client, auth_headers, make_product):
    pid = make_product()["product_id"]
    assert (
        client.post(
            f"/products/{pid}/stock-adjustments",
            json={"quantity_change": 1},
            headers=auth_headers,
        ).status_code
        == 403
    )
    assert (
        client.get(f"/products/{pid}/stock-movements", headers=auth_headers).status_code
        == 403
    )
