import pytest
from fastapi import HTTPException

from app.core.enums import PaymentStatus
from app.models.payment import Payment
from app.services import payment as payment_service_module
from app.services.payment import ALLOWED_TRANSITIONS, transition


def _payment(status, amount="10.00", refunded="0.00"):
    from decimal import Decimal

    return Payment(
        status=status.value,
        amount=Decimal(amount),
        refunded_amount=Decimal(refunded),
        payment_method="card",
    )


@pytest.mark.parametrize(
    "start,end",
    [
        (PaymentStatus.PENDING, PaymentStatus.AUTHORIZED),
        (PaymentStatus.PENDING, PaymentStatus.FAILED),
        (PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED),
        (PaymentStatus.AUTHORIZED, PaymentStatus.FAILED),
        (PaymentStatus.CAPTURED, PaymentStatus.REFUNDED),
    ],
)
def test_legal_transitions(start, end):
    payment = _payment(start)
    assert transition(payment, end).status == end.value


@pytest.mark.parametrize(
    "start,end",
    [
        (PaymentStatus.PENDING, PaymentStatus.CAPTURED),
        (PaymentStatus.PENDING, PaymentStatus.REFUNDED),
        (PaymentStatus.AUTHORIZED, PaymentStatus.REFUNDED),
        (PaymentStatus.CAPTURED, PaymentStatus.FAILED),
        (PaymentStatus.CAPTURED, PaymentStatus.AUTHORIZED),
        (PaymentStatus.FAILED, PaymentStatus.CAPTURED),
        (PaymentStatus.FAILED, PaymentStatus.PENDING),
        (PaymentStatus.REFUNDED, PaymentStatus.CAPTURED),
    ],
)
def test_illegal_transitions_are_rejected(start, end):
    payment = _payment(start)
    with pytest.raises(HTTPException) as error:
        transition(payment, end)
    assert error.value.status_code == 409
    assert payment.status == start.value


def test_every_status_is_covered_by_the_transition_table():
    assert set(ALLOWED_TRANSITIONS) == set(PaymentStatus)
    assert ALLOWED_TRANSITIONS[PaymentStatus.FAILED] == set()
    assert ALLOWED_TRANSITIONS[PaymentStatus.REFUNDED] == set()


def test_only_captured_payments_can_be_refunded():
    with pytest.raises(HTTPException) as error:
        payment_service_module.refund(_payment(PaymentStatus.AUTHORIZED), "1.00")
    assert error.value.status_code == 409


def test_refund_cannot_exceed_what_is_left():
    payment = _payment(PaymentStatus.CAPTURED, amount="10.00", refunded="8.00")
    with pytest.raises(HTTPException):
        payment_service_module.refund(payment, "2.01")


def test_partial_then_full_refund_moves_to_refunded_only_when_complete():
    payment = _payment(PaymentStatus.CAPTURED, amount="10.00")
    payment_service_module.refund(payment, "4.00")
    assert payment.status == PaymentStatus.CAPTURED.value
    payment_service_module.refund(payment, "6.00")
    assert payment.status == PaymentStatus.REFUNDED.value
    assert str(payment.refunded_amount) == "10.00"


def test_cashier_reads_only_their_own_payments_and_receipts(
    client, pos, other_cashier_headers, make_product
):
    product = make_product()
    done = pos.completed_sale(product["product_id"], 1)
    payment_id = done["payment"]["payment_id"]
    receipt_id = done["receipt"]["receipt_id"]
    sale_id = done["sale"]["sale_id"]

    assert client.get(f"/payments/{payment_id}", headers=pos.headers).status_code == 200
    assert client.get(f"/receipts/{receipt_id}", headers=pos.headers).status_code == 200
    assert (
        client.get(f"/payments/{payment_id}", headers=other_cashier_headers).status_code
        == 404
    )
    assert (
        client.get(f"/receipts/{receipt_id}", headers=other_cashier_headers).status_code
        == 404
    )
    assert (
        client.get(
            f"/receipts/by-sale/{sale_id}", headers=other_cashier_headers
        ).status_code
        == 404
    )


def test_managers_and_admins_read_everything(
    client, pos, manager_headers, admin_headers, make_product
):
    product = make_product()
    done = pos.completed_sale(product["product_id"], 1)
    for headers in (manager_headers, admin_headers):
        assert (
            client.get(
                f"/payments/{done['payment']['payment_id']}", headers=headers
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/receipts/{done['receipt']['receipt_id']}", headers=headers
            ).status_code
            == 200
        )
        assert len(client.get("/payments", headers=headers).json()) == 1
        assert len(client.get("/receipts", headers=headers).json()) == 1


def test_cashier_cannot_list_all_payments_or_receipts(client, auth_headers):
    assert client.get("/payments", headers=auth_headers).status_code == 403
    assert client.get("/receipts", headers=auth_headers).status_code == 403


def test_payments_and_receipts_require_login(client):
    assert client.get("/payments").status_code == 401
    assert client.get("/receipts").status_code == 401


def test_payments_and_receipts_are_read_only(client, pos, admin_headers, make_product):
    product = make_product()
    done = pos.completed_sale(product["product_id"], 1)
    for path in (
        f"/payments/{done['payment']['payment_id']}",
        f"/receipts/{done['receipt']['receipt_id']}",
    ):
        assert client.put(path, json={}, headers=admin_headers).status_code == 405
        assert client.delete(path, headers=admin_headers).status_code == 405
    assert client.post("/payments", json={}, headers=admin_headers).status_code == 405
    assert client.post("/receipts", json={}, headers=admin_headers).status_code == 405


def test_unknown_payment_and_receipt_return_404(client, manager_headers):
    zero = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/payments/{zero}", headers=manager_headers).status_code == 404
    assert client.get(f"/receipts/{zero}", headers=manager_headers).status_code == 404
    assert (
        client.get(f"/receipts/by-sale/{zero}", headers=manager_headers).status_code
        == 404
    )


def test_receipt_numbers_are_unique(client, pos, manager_headers, make_product):
    product = make_product(stock_quantity=10)
    numbers = {
        pos.completed_sale(product["product_id"], 1)["receipt"]["receipt_number"]
        for _ in range(3)
    }
    assert len(numbers) == 3
