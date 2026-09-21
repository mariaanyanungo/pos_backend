from decimal import Decimal

from .conftest import get_stock

D = Decimal


def _movements(client, headers, product_id):
    return client.get(f"/products/{product_id}/stock-movements", headers=headers).json()


def test_voiding_an_open_cart_needs_no_manager_and_touches_nothing(client, pos, admin_headers, make_product):
    product = make_product(stock_quantity=10)
    sale = pos.new_sale()["sale_id"]
    pos.add_item(sale, product["product_id"], 3)
    response = client.post(f"/sales/{sale}/void", json={"reason": "customer left"}, headers=pos.headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "voided"
    assert body["void_reason"] == "customer left"
    assert body["voided_at"] is not None
    assert get_stock(client, admin_headers, product["product_id"]) == 10


def test_void_without_body_is_allowed(client, pos):
    sale = pos.new_sale()["sale_id"]
    assert client.post(f"/sales/{sale}/void", headers=pos.headers).status_code == 200


def test_voided_sale_cannot_be_checked_out_or_voided_again(client, pos, make_product):
    product = make_product()
    sale = pos.new_sale()["sale_id"]
    pos.add_item(sale, product["product_id"], 1)
    client.post(f"/sales/{sale}/void", headers=pos.headers)
    assert pos.checkout(sale, "card").status_code == 409
    assert client.post(f"/sales/{sale}/void", headers=pos.headers).status_code == 409


def test_cashier_cannot_void_a_completed_sale(client, pos, admin_headers, make_product):
    product = make_product(stock_quantity=10)
    done = pos.completed_sale(product["product_id"], 2)
    sale_id = done["sale"]["sale_id"]
    response = client.post(f"/sales/{sale_id}/void", headers=pos.headers)
    assert response.status_code == 403
    assert pos.get_sale(sale_id)["status"] == "completed"
    assert get_stock(client, admin_headers, product["product_id"]) == 8


def test_manager_void_of_completed_sale_restores_stock_and_refunds_payment(
    client, pos, manager_headers, admin_headers, make_product
):
    product = make_product(price="10.00", tax_rate="20.00", stock_quantity=10)
    done = pos.completed_sale(product["product_id"], 4)
    sale_id, payment_id = done["sale"]["sale_id"], done["payment"]["payment_id"]
    assert get_stock(client, admin_headers, product["product_id"]) == 6

    response = client.post(f"/sales/{sale_id}/void", json={"reason": "wrong order"}, headers=manager_headers)
    assert response.status_code == 200
    sale = response.json()
    assert sale["status"] == "voided"
    assert all(i["returned_quantity"] == i["quantity"] for i in sale["items"])

    assert get_stock(client, admin_headers, product["product_id"]) == 10
    payment = client.get(f"/payments/{payment_id}", headers=manager_headers).json()
    assert payment["status"] == "refunded"
    assert D(payment["refunded_amount"]) == D(payment["amount"]) == D("48.00")
    reasons = sorted(m["reason"] for m in _movements(client, admin_headers, product["product_id"]))
    assert reasons == ["initial_stock", "sale", "void"]


def test_cashier_cannot_refund(client, pos, make_product):
    product = make_product()
    done = pos.completed_sale(product["product_id"], 1)
    item = done["sale"]["items"][0]
    response = client.post(
        f"/sales/{done['sale']['sale_id']}/refund",
        json={"items": [{"sale_item_id": item["sale_item_id"], "quantity": 1}]},
        headers=pos.headers,
    )
    assert response.status_code == 403


def test_partial_refund_restocks_and_keeps_payment_captured(client, pos, manager_headers, admin_headers, make_product):
    product = make_product(price="10.00", tax_rate="20.00", stock_quantity=10)
    done = pos.completed_sale(product["product_id"], 3)  # 3 x 12.00 = 36.00
    sale_id, item = done["sale"]["sale_id"], done["sale"]["items"][0]

    response = client.post(
        f"/sales/{sale_id}/refund",
        json={"items": [{"sale_item_id": item["sale_item_id"], "quantity": 1}], "reason": "damaged"},
        headers=manager_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert D(body["refunded_amount"]) == D("12.00")
    assert body["sale"]["status"] == "completed" 
    assert body["sale"]["items"][0]["returned_quantity"] == 1
    assert body["payment"]["status"] == "captured"
    assert D(body["payment"]["refunded_amount"]) == D("12.00")
    assert get_stock(client, admin_headers, product["product_id"]) == 8


def test_refund_amounts_add_up_exactly_and_finish_the_sale(client, pos, manager_headers, admin_headers, make_product):
    # 3 x 3.34 = 10.02, minus 0.02 discount => the line is worth exactly 10.00
    product = make_product(price="3.34", tax_rate="0.00", stock_quantity=10)
    done = pos.completed_sale(product["product_id"], 3, discount_amount="0.02")
    assert D(done["payment"]["amount"]) == D("10.00")
    sale_id, item_id = done["sale"]["sale_id"], done["sale"]["items"][0]["sale_item_id"]

    amounts = []
    last = None
    for _ in range(3):
        last = client.post(
            f"/sales/{sale_id}/refund",
            json={"items": [{"sale_item_id": item_id, "quantity": 1}]},
            headers=manager_headers,
        )
        assert last.status_code == 200, last.text
        amounts.append(D(last.json()["refunded_amount"]))

    assert amounts == [D("3.33"), D("3.33"), D("3.34")]
    assert sum(amounts) == D("10.00")
    final = last.json()
    assert final["sale"]["status"] == "refunded"
    assert final["payment"]["status"] == "refunded"
    assert D(final["payment"]["refunded_amount"]) == D("10.00")
    assert get_stock(client, admin_headers, product["product_id"]) == 10


def test_cannot_return_more_than_was_bought(client, pos, manager_headers, admin_headers, make_product):
    product = make_product(stock_quantity=10)
    done = pos.completed_sale(product["product_id"], 2)
    sale_id, item_id = done["sale"]["sale_id"], done["sale"]["items"][0]["sale_item_id"]
    url = f"/sales/{sale_id}/refund"

    too_many = client.post(url, json={"items": [{"sale_item_id": item_id, "quantity": 3}]}, headers=manager_headers)
    assert too_many.status_code == 409
    split_too_many = client.post(
        url,
        json={"items": [{"sale_item_id": item_id, "quantity": 2}, {"sale_item_id": item_id, "quantity": 1}]},
        headers=manager_headers,
    )
    assert split_too_many.status_code == 409 
    assert get_stock(client, admin_headers, product["product_id"]) == 8

    assert client.post(url, json={"items": [{"sale_item_id": item_id, "quantity": 2}]}, headers=manager_headers).status_code == 200
    again = client.post(url, json={"items": [{"sale_item_id": item_id, "quantity": 1}]}, headers=manager_headers)
    assert again.status_code == 409  


def test_refund_of_an_item_from_another_sale_is_rejected(client, pos, manager_headers, make_product):
    product = make_product(stock_quantity=10)
    first = pos.completed_sale(product["product_id"], 1)
    second = pos.completed_sale(product["product_id"], 1)
    foreign_item = second["sale"]["items"][0]["sale_item_id"]
    response = client.post(
        f"/sales/{first['sale']['sale_id']}/refund",
        json={"items": [{"sale_item_id": foreign_item, "quantity": 1}]},
        headers=manager_headers,
    )
    assert response.status_code == 404


def test_open_sale_cannot_be_refunded(client, pos, manager_headers, make_product):
    product = make_product()
    sale = pos.new_sale()["sale_id"]
    cart = pos.add_item(sale, product["product_id"], 1)
    response = client.post(
        f"/sales/{sale}/refund",
        json={"items": [{"sale_item_id": cart["items"][0]["sale_item_id"], "quantity": 1}]},
        headers=manager_headers,
    )
    assert response.status_code == 409


def test_refund_validation(client, pos, manager_headers, make_product):
    product = make_product()
    done = pos.completed_sale(product["product_id"], 1)
    url = f"/sales/{done['sale']['sale_id']}/refund"
    item_id = done["sale"]["items"][0]["sale_item_id"]
    assert client.post(url, json={"items": []}, headers=manager_headers).status_code == 422
    assert client.post(url, json={"items": [{"sale_item_id": item_id, "quantity": 0}]}, headers=manager_headers).status_code == 422


def test_void_after_a_partial_refund_only_returns_the_rest(client, pos, manager_headers, admin_headers, make_product):
    product = make_product(price="10.00", tax_rate="0.00", stock_quantity=10)
    done = pos.completed_sale(product["product_id"], 4)  # 40.00
    sale_id, item_id = done["sale"]["sale_id"], done["sale"]["items"][0]["sale_item_id"]
    client.post(
        f"/sales/{sale_id}/refund",
        json={"items": [{"sale_item_id": item_id, "quantity": 1}]},
        headers=manager_headers,
    )
    voided = client.post(f"/sales/{sale_id}/void", headers=manager_headers)
    assert voided.status_code == 200
    payment = client.get(f"/payments/{done['payment']['payment_id']}", headers=manager_headers).json()
    assert payment["status"] == "refunded"
    assert D(payment["refunded_amount"]) == D("40.00")
    assert get_stock(client, admin_headers, product["product_id"]) == 10 


def test_refunded_sale_keeps_its_receipt(client, pos, manager_headers, make_product):
    product = make_product()
    done = pos.completed_sale(product["product_id"], 1)
    sale_id = done["sale"]["sale_id"]
    client.post(f"/sales/{sale_id}/void", headers=manager_headers)
    assert client.get(f"/receipts/by-sale/{sale_id}", headers=manager_headers).status_code == 200