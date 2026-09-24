from decimal import Decimal

from app.services import payment_gateway
from app.services.payment_gateway import (
    GatewayError,
    GatewayResult,
    SimulatedCardGateway,
)

from .conftest import get_stock

D = Decimal


def _cart(pos, make_product, *, quantity=2, **product_kwargs):
    product = make_product(**product_kwargs)
    sale = pos.new_sale()
    cart = pos.add_item(sale["sale_id"], product["product_id"], quantity)
    return product, sale["sale_id"], cart


def _payments(client, manager_headers, sale_id):
    return client.get(f"/payments?sale_id={sale_id}", headers=manager_headers).json()


def test_cash_checkout_completes_sale_deducts_stock_and_issues_receipt(
    client, pos, admin_headers, make_product
):
    product, sale_id, cart = _cart(
        pos,
        make_product,
        quantity=2,
        price="10.00",
        tax_rate="20.00",
        stock_quantity=10,
    )
    assert D(cart["total_amount"]) == D("24.00")

    response = pos.checkout(sale_id, "cash", tendered="30.00")
    assert response.status_code == 201
    assert "idempotent-replay" not in response.headers
    body = response.json()

    assert body["sale"]["status"] == "completed"
    assert body["sale"]["completed_at"] is not None
    payment = body["payment"]
    assert payment["status"] == "captured"
    assert payment["payment_method"] == "cash"
    assert (
        D(payment["amount"]),
        D(payment["amount_tendered"]),
        D(payment["change_due"]),
    ) == (
        D("24.00"),
        D("30.00"),
        D("6.00"),
    )
    assert payment["captured_at"] is not None

    receipt = body["receipt"]
    assert receipt["receipt_number"].startswith("R")
    assert (D(receipt["subtotal"]), D(receipt["vat"]), D(receipt["total_amount"])) == (
        D("20.00"),
        D("4.00"),
        D("24.00"),
    )
    assert (D(receipt["amount_tendered"]), D(receipt["change_due"])) == (
        D("30.00"),
        D("6.00"),
    )
    assert (
        receipt["sale_id"] == sale_id and receipt["payment_id"] == payment["payment_id"]
    )

    assert get_stock(client, admin_headers, product["product_id"]) == 8
    ledger = client.get(
        f"/products/{product['product_id']}/stock-movements", headers=admin_headers
    ).json()
    sale_moves = [m for m in ledger if m["reason"] == "sale"]
    assert [(m["quantity_change"], m["sale_id"]) for m in sale_moves] == [(-2, sale_id)]


def test_exact_cash_has_no_change(client, pos, make_product):
    _, sale_id, cart = _cart(
        pos, make_product, quantity=1, price="10.00", tax_rate="0.00"
    )
    body = pos.checkout(sale_id, "cash", tendered=cart["total_amount"]).json()
    assert D(body["payment"]["change_due"]) == D("0.00")


def test_card_checkout(client, pos, admin_headers, make_product):
    product, sale_id, cart = _cart(
        pos, make_product, quantity=1, price="10.00", tax_rate="20.00"
    )
    response = pos.checkout(sale_id, "card")
    assert response.status_code == 201
    payment = response.json()["payment"]
    assert payment["status"] == "captured"
    assert payment["payment_method"] == "card"
    assert payment["gateway_reference"].startswith("CARD-")
    assert D(payment["amount"]) == D("12.00")
    assert D(payment["change_due"]) == D("0.00")
    assert get_stock(client, admin_headers, product["product_id"]) == 9


def test_card_with_matching_explicit_tender_is_accepted(client, pos, make_product):
    _, sale_id, cart = _cart(
        pos, make_product, quantity=1, price="10.00", tax_rate="0.00"
    )
    assert pos.checkout(sale_id, "card", tendered="10.00").status_code == 201


def test_receipt_and_payment_are_readable_after_checkout(client, pos, make_product):
    _, sale_id, _ = _cart(pos, make_product)
    body = pos.checkout(sale_id, "card").json()
    by_id = client.get(
        f"/receipts/{body['receipt']['receipt_id']}", headers=pos.headers
    )
    by_sale = client.get(f"/receipts/by-sale/{sale_id}", headers=pos.headers)
    assert by_id.status_code == by_sale.status_code == 200
    assert by_id.json() == by_sale.json()
    assert (
        client.get(
            f"/payments/{body['payment']['payment_id']}", headers=pos.headers
        ).status_code
        == 200
    )


def test_cash_requires_amount_tendered(client, pos, make_product):
    _, sale_id, _ = _cart(pos, make_product)
    response = pos.checkout(sale_id, "cash")
    assert response.status_code == 422


def test_insufficient_cash_is_rejected_and_nothing_changes(
    client, pos, admin_headers, manager_headers, make_product
):
    product, sale_id, cart = _cart(
        pos, make_product, quantity=1, price="10.00", tax_rate="0.00", stock_quantity=5
    )
    response = pos.checkout(sale_id, "cash", tendered="9.99")
    assert response.status_code == 422
    assert "Insufficient cash" in response.json()["detail"]
    assert pos.get_sale(sale_id)["status"] == "open"
    assert get_stock(client, admin_headers, product["product_id"]) == 5
    assert _payments(client, manager_headers, sale_id) == []


def test_card_with_wrong_explicit_tender_is_rejected(client, pos, make_product):
    _, sale_id, _ = _cart(pos, make_product, quantity=1, price="10.00", tax_rate="0.00")
    assert pos.checkout(sale_id, "card", tendered="20.00").status_code == 422


def test_unknown_payment_method_returns_422(client, pos, make_product):
    _, sale_id, _ = _cart(pos, make_product)
    response = client.post(
        f"/sales/{sale_id}/checkout",
        json={"payment_method": "bitcoin"},
        headers={**pos.headers, "Idempotency-Key": "k"},
    )
    assert response.status_code == 422


def test_empty_sale_cannot_be_checked_out(client, pos):
    sale = pos.new_sale()
    response = pos.checkout(sale["sale_id"], "card")
    assert response.status_code == 422


def test_idempotency_key_header_is_required(client, pos, make_product):
    _, sale_id, _ = _cart(pos, make_product)
    response = client.post(
        f"/sales/{sale_id}/checkout",
        json={"payment_method": "card"},
        headers=pos.headers,
    )
    assert response.status_code == 422


def test_checkout_of_unknown_sale_returns_404(client, pos):
    assert (
        pos.checkout("00000000-0000-0000-0000-000000000000", "card").status_code == 404
    )


def test_cashier_cannot_check_out_someone_elses_sale(
    client, pos, other_cashier_headers, make_product
):
    _, sale_id, _ = _cart(pos, make_product)
    response = pos.checkout(sale_id, "card", headers=other_cashier_headers)
    assert response.status_code == 404


def test_a_paid_sale_cannot_be_checked_out_again_with_a_new_key(
    client, pos, admin_headers, make_product
):
    product, sale_id, _ = _cart(pos, make_product, stock_quantity=10)
    assert pos.checkout(sale_id, "card", key="first").status_code == 201
    second = pos.checkout(sale_id, "card", key="second")
    assert second.status_code == 409
    assert (
        get_stock(client, admin_headers, product["product_id"]) == 8
    )  # deducted once only


def test_insufficient_stock_at_checkout_rolls_everything_back(
    client, pos, admin_headers, manager_headers, make_product
):
    scarce = make_product(price="10.00", tax_rate="0.00", stock_quantity=3)
    plenty = make_product(price="5.00", tax_rate="0.00", stock_quantity=50)
    first = pos.new_sale()["sale_id"]
    second = pos.new_sale()["sale_id"]

    for sale_id in (first, second):
        pos.add_item(sale_id, scarce["product_id"], 2)
        pos.add_item(sale_id, plenty["product_id"], 4)

    assert pos.checkout(first, "card").status_code == 201
    assert get_stock(client, admin_headers, scarce["product_id"]) == 1

    response = pos.checkout(second, "card")
    assert response.status_code == 409
    assert "Insufficient stock" in response.json()["detail"]
    assert scarce["name"] in response.json()["detail"]

    assert pos.get_sale(second)["status"] == "open"
    assert get_stock(client, admin_headers, scarce["product_id"]) == 1
    assert get_stock(client, admin_headers, plenty["product_id"]) == 46
    assert _payments(client, manager_headers, second) == []


def test_product_deactivated_after_carting_blocks_checkout(
    client, pos, admin_headers, make_product
):
    product, sale_id, _ = _cart(pos, make_product, stock_quantity=10)
    client.delete(f"/products/{product['product_id']}", headers=admin_headers)
    response = pos.checkout(sale_id, "card")
    assert response.status_code == 409
    assert "no longer available" in response.json()["detail"]
    assert get_stock(client, admin_headers, product["product_id"]) == 10


def test_selling_the_last_unit_leaves_zero_stock(
    client, pos, admin_headers, make_product
):
    product, sale_id, _ = _cart(pos, make_product, quantity=3, stock_quantity=3)
    assert pos.checkout(sale_id, "card").status_code == 201
    assert get_stock(client, admin_headers, product["product_id"]) == 0


def test_replaying_the_same_key_returns_the_original_result_without_charging_twice(
    client, pos, admin_headers, manager_headers, make_product
):
    product, sale_id, _ = _cart(pos, make_product, quantity=2, stock_quantity=10)
    first = pos.checkout(sale_id, "card", key="order-1")
    replay = pos.checkout(sale_id, "card", key="order-1")

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.headers["idempotent-replay"] == "true"
    assert (
        replay.json()["payment"]["payment_id"] == first.json()["payment"]["payment_id"]
    )
    assert (
        replay.json()["receipt"]["receipt_id"] == first.json()["receipt"]["receipt_id"]
    )
    assert get_stock(client, admin_headers, product["product_id"]) == 8
    assert len(_payments(client, manager_headers, sale_id)) == 1


def test_same_key_with_a_different_request_is_rejected(client, pos, make_product):
    _, sale_id, _ = _cart(pos, make_product, quantity=1, price="10.00", tax_rate="0.00")
    assert pos.checkout(sale_id, "cash", tendered="10.00", key="k-1").status_code == 201
    other_method = pos.checkout(sale_id, "card", key="k-1")
    other_tender = pos.checkout(sale_id, "cash", tendered="20.00", key="k-1")
    assert other_method.status_code == 422
    assert other_tender.status_code == 422
    assert "different request" in other_method.json()["detail"]


def test_same_key_on_another_sale_is_rejected(client, pos, make_product):
    product = make_product()
    first = pos.new_sale()["sale_id"]
    second = pos.new_sale()["sale_id"]
    pos.add_item(first, product["product_id"], 1)
    pos.add_item(second, product["product_id"], 1)
    assert pos.checkout(first, "card", key="shared").status_code == 201
    assert pos.checkout(second, "card", key="shared").status_code == 422
    assert pos.get_sale(second)["status"] == "open"


def test_another_cashier_cannot_replay_a_key_to_read_the_result(
    client, pos, other_cashier_headers, make_product
):
    _, sale_id, _ = _cart(pos, make_product)
    pos.checkout(sale_id, "card", key="secret-key")
    response = pos.checkout(
        sale_id, "card", key="secret-key", headers=other_cashier_headers
    )
    assert response.status_code == 404


class DecliningGateway:
    def authorize(self, amount, idempotency_key):
        return GatewayResult(
            approved=False, failure_reason="Card declined: insufficient funds"
        )

    def capture(self, reference, amount):
        raise AssertionError("must not capture a declined authorization")

    def void(self, reference):
        return GatewayResult(approved=True)

    def refund(self, reference, amount):
        return GatewayResult(approved=True)


class CaptureFailsGateway(SimulatedCardGateway):
    def __init__(self):
        self.voided = []

    def capture(self, reference, amount):
        return GatewayResult(approved=False, failure_reason="Capture failed")

    def void(self, reference):
        self.voided.append(reference)
        return GatewayResult(approved=True, reference=reference)


class DownGateway(SimulatedCardGateway):
    def authorize(self, amount, idempotency_key):
        raise GatewayError("timeout")


def test_declined_card_leaves_sale_open_stock_untouched_and_records_failed_payment(
    client, pos, admin_headers, manager_headers, make_product, monkeypatch
):
    product, sale_id, _ = _cart(pos, make_product, quantity=2, stock_quantity=10)
    monkeypatch.setitem(payment_gateway.GATEWAYS, "card", DecliningGateway())

    response = pos.checkout(sale_id, "card", key="try-1")
    assert response.status_code == 402
    assert response.json()["detail"] == "Card declined: insufficient funds"

    assert pos.get_sale(sale_id)["status"] == "open"
    assert get_stock(client, admin_headers, product["product_id"]) == 10
    payments = _payments(client, manager_headers, sale_id)
    assert [p["status"] for p in payments] == ["failed"]
    assert payments[0]["failure_reason"] == "Card declined: insufficient funds"
    assert (
        client.get(f"/receipts/by-sale/{sale_id}", headers=pos.headers).status_code
        == 404
    )

    assert pos.checkout(sale_id, "card", key="try-1").status_code == 402
    assert len(_payments(client, manager_headers, sale_id)) == 1

    # the customer tries again (new key) once the gateway works
    monkeypatch.setitem(payment_gateway.GATEWAYS, "card", SimulatedCardGateway())
    retry = pos.checkout(sale_id, "card", key="try-2")
    assert retry.status_code == 201
    assert get_stock(client, admin_headers, product["product_id"]) == 8
    assert sorted(p["status"] for p in _payments(client, manager_headers, sale_id)) == [
        "captured",
        "failed",
    ]


def test_failed_capture_voids_the_authorization_and_rolls_back(
    client, pos, admin_headers, manager_headers, make_product, monkeypatch
):
    product, sale_id, _ = _cart(pos, make_product, stock_quantity=10)
    gateway = CaptureFailsGateway()
    monkeypatch.setitem(payment_gateway.GATEWAYS, "card", gateway)

    response = pos.checkout(sale_id, "card")
    assert response.status_code == 402
    assert len(gateway.voided) == 1
    assert pos.get_sale(sale_id)["status"] == "open"
    assert get_stock(client, admin_headers, product["product_id"]) == 10
    assert [p["status"] for p in _payments(client, manager_headers, sale_id)] == [
        "failed"
    ]


def test_gateway_outage_returns_502_and_can_be_retried_with_the_same_key(
    client, pos, admin_headers, manager_headers, make_product, monkeypatch
):
    product, sale_id, _ = _cart(pos, make_product, stock_quantity=10)
    monkeypatch.setitem(payment_gateway.GATEWAYS, "card", DownGateway())
    assert pos.checkout(sale_id, "card", key="retry-me").status_code == 502
    assert get_stock(client, admin_headers, product["product_id"]) == 10
    assert _payments(client, manager_headers, sale_id) == []

    monkeypatch.setitem(payment_gateway.GATEWAYS, "card", SimulatedCardGateway())
    assert pos.checkout(sale_id, "card", key="retry-me").status_code == 201
    assert get_stock(client, admin_headers, product["product_id"]) == 8


def test_zero_total_sale_can_be_paid(client, pos, make_product):
    product = make_product(price="5.00", tax_rate="20.00")
    sale = pos.new_sale()["sale_id"]
    pos.add_item(sale, product["product_id"], 1, discount_percent="100")
    response = pos.checkout(sale, "cash", tendered="0.00")
    assert response.status_code == 201
    assert D(response.json()["payment"]["amount"]) == D("0.00")
