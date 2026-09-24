from dataclasses import replace
from decimal import Decimal

from app.services import sale as sale_service

D = Decimal


def test_create_sale_starts_open_and_empty(client, pos):
    sale = pos.new_sale()
    assert sale["status"] == "open"
    assert sale["items"] == []
    assert D(sale["total_amount"]) == D("0.00")
    assert sale["customer_id"] is None
    assert sale["prices_include_tax"] is False


def test_sales_require_login(client):
    assert client.post("/sales", json={}).status_code == 401


def test_sale_can_be_linked_to_a_customer(client, pos, auth_headers):
    customer = client.post(
        "/customers", json={"name": "Jane"}, headers=auth_headers
    ).json()
    sale = pos.new_sale(customer_id=customer["customer_id"])
    assert sale["customer_id"] == customer["customer_id"]


def test_sale_with_unknown_customer_returns_422(client, auth_headers):
    response = client.post(
        "/sales",
        json={"customer_id": "00000000-0000-0000-0000-000000000000"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_add_item_snapshots_product_and_calculates_totals(client, pos, make_product):
    product = make_product(name="Cola", price="10.00", tax_rate="20.00", barcode="111")
    sale = pos.new_sale()
    cart = pos.add_item(sale["sale_id"], product["product_id"], quantity=3)
    line = cart["items"][0]
    assert line["product_name"] == "Cola"
    assert line["barcode"] == "111"
    assert D(line["unit_price"]) == D("10.00")
    assert (D(line["line_subtotal"]), D(line["tax_amount"]), D(line["line_total"])) == (
        D("30.00"),
        D("6.00"),
        D("36.00"),
    )
    assert (D(cart["subtotal"]), D(cart["tax_total"]), D(cart["total_amount"])) == (
        D("30.00"),
        D("6.00"),
        D("36.00"),
    )


def test_add_item_by_barcode(client, pos, make_product):
    product = make_product(barcode="5449000000996")
    sale = pos.new_sale()
    response = client.post(
        f"/sales/{sale['sale_id']}/items",
        json={"barcode": "5449000000996", "quantity": 2},
        headers=pos.headers,
    )
    assert response.status_code == 201
    assert response.json()["items"][0]["product_id"] == product["product_id"]


def test_adding_the_same_product_twice_merges_into_one_line(client, pos, make_product):
    product = make_product()
    sale = pos.new_sale()
    pos.add_item(sale["sale_id"], product["product_id"], 2)
    cart = pos.add_item(sale["sale_id"], product["product_id"], 3)
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 5


def test_price_is_frozen_when_added_to_cart(client, pos, admin_headers, make_product):
    product = make_product(price="10.00", tax_rate="0.00")
    sale = pos.new_sale()
    pos.add_item(sale["sale_id"], product["product_id"], 1)
    client.put(
        f"/products/{product['product_id']}",
        json={"price": "99.00"},
        headers=admin_headers,
    )
    assert D(pos.get_sale(sale["sale_id"])["total_amount"]) == D("10.00")


def test_totals_stay_exact_with_awkward_cents(client, pos, make_product):
    product = make_product(price="0.99", tax_rate="7.00")
    sale = pos.new_sale()
    cart = pos.add_item(sale["sale_id"], product["product_id"], 3)
    assert (D(cart["subtotal"]), D(cart["tax_total"]), D(cart["total_amount"])) == (
        D("2.97"),
        D("0.21"),
        D("3.18"),
    )


def test_fixed_and_percent_discounts(client, pos, make_product):
    product = make_product(price="50.00", tax_rate="8.50")
    other = make_product(price="19.99", tax_rate="0.00")
    sale = pos.new_sale()
    pos.add_item(sale["sale_id"], product["product_id"], 2, discount_amount="10.00")
    cart = pos.add_item(sale["sale_id"], other["product_id"], 1, discount_percent="15")
    lines = {line["product_id"]: line for line in cart["items"]}
    assert D(lines[product["product_id"]]["line_total"]) == D("97.65")
    assert D(lines[other["product_id"]]["discount_amount"]) == D("3.00")
    assert D(cart["discount_total"]) == D("13.00")
    assert D(cart["total_amount"]) == D("97.65") + D("16.99")


def test_invalid_discounts_are_rejected(client, pos, make_product):
    product = make_product(price="10.00")
    sale = pos.new_sale()
    url = f"/sales/{sale['sale_id']}/items"
    base = {"product_id": product["product_id"], "quantity": 1}
    assert (
        client.post(
            url, json={**base, "discount_amount": "10.01"}, headers=pos.headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, json={**base, "discount_percent": "100.01"}, headers=pos.headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, json={**base, "discount_amount": "-1"}, headers=pos.headers
        ).status_code
        == 422
    )
    both = {**base, "discount_amount": "1.00", "discount_percent": "5"}
    assert client.post(url, json=both, headers=pos.headers).status_code == 422


def test_item_needs_exactly_one_of_product_id_or_barcode(client, pos, make_product):
    product = make_product()
    sale = pos.new_sale()
    url = f"/sales/{sale['sale_id']}/items"
    assert (
        client.post(url, json={"quantity": 1}, headers=pos.headers).status_code == 422
    )
    both = {"product_id": product["product_id"], "barcode": "x", "quantity": 1}
    assert client.post(url, json=both, headers=pos.headers).status_code == 422
    assert (
        client.post(
            url,
            json={"product_id": product["product_id"], "quantity": 0},
            headers=pos.headers,
        ).status_code
        == 422
    )


def test_unknown_and_inactive_products_cannot_be_added(
    client, pos, admin_headers, make_product
):
    sale = pos.new_sale()
    url = f"/sales/{sale['sale_id']}/items"
    missing = client.post(
        url,
        json={"product_id": "00000000-0000-0000-0000-000000000000"},
        headers=pos.headers,
    )
    assert missing.status_code == 404
    product = make_product()
    client.delete(f"/products/{product['product_id']}", headers=admin_headers)
    inactive = client.post(
        url, json={"product_id": product["product_id"]}, headers=pos.headers
    )
    assert inactive.status_code == 409


def test_cannot_add_more_than_the_stock_on_hand(client, pos, make_product):
    product = make_product(stock_quantity=3)
    sale = pos.new_sale()
    url = f"/sales/{sale['sale_id']}/items"
    response = client.post(
        url,
        json={"product_id": product["product_id"], "quantity": 4},
        headers=pos.headers,
    )
    assert response.status_code == 409
    assert "Insufficient stock" in response.json()["detail"]
    pos.add_item(sale["sale_id"], product["product_id"], 3)
    again = client.post(
        url,
        json={"product_id": product["product_id"], "quantity": 1},
        headers=pos.headers,
    )
    assert again.status_code == 409  # merged quantity would be 4


def test_update_item_quantity_and_discount(client, pos, make_product):
    product = make_product(price="10.00", tax_rate="0.00")
    sale = pos.new_sale()
    cart = pos.add_item(
        sale["sale_id"], product["product_id"], 1, discount_percent="10"
    )
    item_id = cart["items"][0]["sale_item_id"]
    url = f"/sales/{sale['sale_id']}/items/{item_id}"

    updated = client.patch(url, json={"quantity": 4}, headers=pos.headers).json()
    assert D(updated["items"][0]["discount_amount"]) == D(
        "4.00"
    )  # percent follows the quantity
    assert D(updated["total_amount"]) == D("36.00")

    cleared = client.patch(
        url, json={"discount_percent": None}, headers=pos.headers
    ).json()
    assert D(cleared["items"][0]["discount_amount"]) == D("0.00")
    assert D(cleared["total_amount"]) == D("40.00")

    fixed = client.patch(
        url, json={"discount_amount": "5.00"}, headers=pos.headers
    ).json()
    assert D(fixed["total_amount"]) == D("35.00")


def test_update_item_validation(client, pos, make_product):
    product = make_product(stock_quantity=5)
    sale = pos.new_sale()
    item_id = pos.add_item(sale["sale_id"], product["product_id"], 1)["items"][0][
        "sale_item_id"
    ]
    url = f"/sales/{sale['sale_id']}/items/{item_id}"
    assert (
        client.patch(url, json={"quantity": 0}, headers=pos.headers).status_code == 422
    )
    assert (
        client.patch(url, json={"quantity": 6}, headers=pos.headers).status_code == 409
    )
    assert (
        client.patch(
            url, json={"discount_amount": "10.01"}, headers=pos.headers
        ).status_code
        == 422
    )
    unknown = f"/sales/{sale['sale_id']}/items/00000000-0000-0000-0000-000000000000"
    assert (
        client.patch(unknown, json={"quantity": 1}, headers=pos.headers).status_code
        == 404
    )


def test_remove_item_updates_totals(client, pos, make_product):
    first = make_product(price="10.00", tax_rate="0.00")
    second = make_product(price="5.00", tax_rate="0.00")
    sale = pos.new_sale()
    pos.add_item(sale["sale_id"], first["product_id"], 1)
    cart = pos.add_item(sale["sale_id"], second["product_id"], 2)
    item_id = next(
        i["sale_item_id"]
        for i in cart["items"]
        if i["product_id"] == first["product_id"]
    )
    response = client.delete(
        f"/sales/{sale['sale_id']}/items/{item_id}", headers=pos.headers
    )
    assert response.status_code == 200
    body = response.json()
    assert [i["product_id"] for i in body["items"]] == [second["product_id"]]
    assert D(body["total_amount"]) == D("10.00")


def test_cart_does_not_touch_stock(client, pos, admin_headers, make_product):
    from .conftest import get_stock

    product = make_product(stock_quantity=10)
    sale = pos.new_sale()
    pos.add_item(sale["sale_id"], product["product_id"], 4)
    assert get_stock(client, admin_headers, product["product_id"]) == 10


def test_items_cannot_change_after_the_sale_is_closed(client, pos, make_product):
    product = make_product()
    sale = pos.new_sale()
    cart = pos.add_item(sale["sale_id"], product["product_id"], 1)
    item_id = cart["items"][0]["sale_item_id"]
    assert (
        client.post(f"/sales/{sale['sale_id']}/void", headers=pos.headers).status_code
        == 200
    )
    url = f"/sales/{sale['sale_id']}/items"
    assert (
        client.post(
            url, json={"product_id": product["product_id"]}, headers=pos.headers
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"{url}/{item_id}", json={"quantity": 2}, headers=pos.headers
        ).status_code
        == 409
    )
    assert client.delete(f"{url}/{item_id}", headers=pos.headers).status_code == 409


def test_cashiers_only_see_their_own_sales(
    client, pos, other_cashier_headers, manager_headers
):
    sale = pos.new_sale()
    foreign = f"/sales/{sale['sale_id']}"
    assert client.get(foreign, headers=other_cashier_headers).status_code == 404
    assert (
        client.post(
            f"{foreign}/items", json={"barcode": "x"}, headers=other_cashier_headers
        ).status_code
        == 404
    )
    assert client.get("/sales", headers=other_cashier_headers).json() == []
    assert client.get(foreign, headers=manager_headers).status_code == 200
    assert [
        s["sale_id"] for s in client.get("/sales", headers=manager_headers).json()
    ] == [sale["sale_id"]]


def test_list_sales_filters_by_status(client, pos):
    open_sale = pos.new_sale()
    voided = pos.new_sale()
    client.post(f"/sales/{voided['sale_id']}/void", headers=pos.headers)
    open_ids = [
        s["sale_id"]
        for s in client.get("/sales?status=open", headers=pos.headers).json()
    ]
    assert open_ids == [open_sale["sale_id"]]


def test_get_unknown_sale_returns_404(client, auth_headers):
    assert (
        client.get(
            "/sales/00000000-0000-0000-0000-000000000000", headers=auth_headers
        ).status_code
        == 404
    )


def test_tax_inclusive_pricing_mode(client, pos, make_product, monkeypatch):
    monkeypatch.setattr(
        sale_service,
        "settings",
        replace(sale_service.settings, prices_include_tax=True),
    )
    product = make_product(price="12.00", tax_rate="20.00")
    sale = pos.new_sale()
    assert sale["prices_include_tax"] is True
    cart = pos.add_item(sale["sale_id"], product["product_id"], 1)
    assert (D(cart["subtotal"]), D(cart["tax_total"]), D(cart["total_amount"])) == (
        D("12.00"),
        D("2.00"),
        D("12.00"),
    )
