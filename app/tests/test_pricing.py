from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.money import money
from app.services import pricing
from app.services.pricing import PricingError, calculate_line, refund_amount_for_units

D = Decimal


def test_money_rounds_half_up_not_bankers():
    assert money("0.025") == D("0.03")
    assert money("0.035") == D("0.04")
    assert money("2.675") == D("2.68")
    assert money(1) == D("1.00")
    assert money(0.1 + 0.2) == D("0.30") 


def test_line_without_tax_or_discount():
    line = calculate_line("4.50", 4, "0")
    assert (line.gross, line.discount, line.tax, line.total) == (D("18.00"), D("0.00"), D("0.00"), D("18.00"))


def test_line_tax_exclusive():
    line = calculate_line("10.00", 3, "20.00")
    assert (line.gross, line.tax, line.total) == (D("30.00"), D("6.00"), D("36.00"))


def test_line_tax_exclusive_rounds_half_up():
    line = calculate_line("0.25", 1, "10.00")
    assert line.tax == D("0.03")
    assert line.total == D("0.28")


def test_line_tax_exclusive_small_fractions():
    # 2.97 * 7% = 0.2079 -> 0.21
    line = calculate_line("0.99", 3, "7.00")
    assert (line.gross, line.tax, line.total) == (D("2.97"), D("0.21"), D("3.18"))


def test_line_tax_inclusive_extracts_tax_from_price():
    line = calculate_line("12.00", 1, "20.00", prices_include_tax=True)
    assert (line.gross, line.tax, line.total) == (D("12.00"), D("2.00"), D("12.00"))


def test_line_tax_inclusive_rounding():
    # 9.99 - 9.99/1.21 = 1.7338... -> 1.73
    line = calculate_line("9.99", 1, "21.00", prices_include_tax=True)
    assert line.tax == D("1.73")
    assert line.total == D("9.99")


def test_fixed_discount_reduces_taxable_amount():
    line = calculate_line("50.00", 2, "8.50", discount_amount="10.00")
    assert (line.gross, line.discount, line.tax, line.total) == (D("100.00"), D("10.00"), D("7.65"), D("97.65"))


def test_percent_discount_rounds_half_up():
    # 19.99 * 15% = 2.9985 -> 3.00
    line = calculate_line("19.99", 1, "0", discount_percent="15")
    assert (line.discount, line.total) == (D("3.00"), D("16.99"))


def test_full_discount_gives_zero_total():
    line = calculate_line("5.00", 2, "20.00", discount_percent="100")
    assert (line.discount, line.tax, line.total) == (D("10.00"), D("0.00"), D("0.00"))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"quantity": 0},
        {"quantity": -1},
        {"quantity": True},
        {"quantity": 1, "unit_price": "-1.00"},
        {"quantity": 1, "tax_rate": "101"},
        {"quantity": 1, "tax_rate": "-1"},
        {"quantity": 1, "discount_amount": "10.01"},
        {"quantity": 1, "discount_percent": "100.01"},
        {"quantity": 1, "discount_amount": "-1.00"},
    ],
)
def test_invalid_input_is_rejected(kwargs):
    args = {"unit_price": "10.00", "tax_rate": "0"}
    args.update(kwargs)
    with pytest.raises(PricingError):
        calculate_line(args.pop("unit_price"), args.pop("quantity"), args.pop("tax_rate"), **args)


def _item(price, qty, tax="0", percent=None, amount="0.00"):
    return SimpleNamespace(
        unit_price=D(price),
        quantity=qty,
        tax_rate=D(tax),
        discount_percent=None if percent is None else D(percent),
        discount_amount=D(amount),
        line_subtotal=D("0"),
        tax_amount=D("0"),
        line_total=D("0"),
    )


def test_recalculate_sale_totals_add_up_exactly():
    sale = SimpleNamespace(
        prices_include_tax=False,
        items=[_item("0.99", 3, "7"), _item("19.99", 1, "0", percent="15"), _item("10.00", 2, "20", amount="1.00")],
        subtotal=None,
        discount_total=None,
        tax_total=None,
        total_amount=None,
    )
    pricing.recalculate_sale(sale)
    assert sale.subtotal == D("2.97") + D("19.99") + D("20.00")
    assert sale.discount_total == D("3.00") + D("1.00")
    assert sale.tax_total == sum(item.tax_amount for item in sale.items)
    # exclusive pricing: total = subtotal - discount + tax
    assert sale.total_amount == sale.subtotal - sale.discount_total + sale.tax_total
    assert sale.total_amount == sum(item.line_total for item in sale.items)


def test_recalculate_sale_inclusive_total_excludes_added_tax():
    sale = SimpleNamespace(
        prices_include_tax=True,
        items=[_item("12.00", 1, "20")],
        subtotal=None,
        discount_total=None,
        tax_total=None,
        total_amount=None,
    )
    pricing.recalculate_sale(sale)
    assert (sale.subtotal, sale.tax_total, sale.total_amount) == (D("12.00"), D("2.00"), D("12.00"))


def test_percent_mode_discount_follows_quantity_changes():
    item = _item("10.00", 1, percent="10")
    pricing.apply_line_pricing(item, False)
    assert item.discount_amount == D("1.00")
    item.quantity = 3
    pricing.apply_line_pricing(item, False)
    assert item.discount_amount == D("3.00")


def test_refund_amounts_add_up_to_the_line_total_exactly():
    line_total, quantity = D("10.00"), 3
    refunded = D("0.00")
    returned = 0
    amounts = []
    for _ in range(quantity):
        amount = refund_amount_for_units(
            line_total=line_total,
            quantity=quantity,
            units_already_returned=returned,
            amount_already_refunded=refunded,
            units=1,
        )
        amounts.append(amount)
        refunded += amount
        returned += 1
    assert amounts == [D("3.33"), D("3.33"), D("3.34")]
    assert refunded == line_total


def test_refund_of_all_units_at_once_is_the_whole_line():
    amount = refund_amount_for_units(
        line_total=D("10.00"), quantity=3, units_already_returned=0, amount_already_refunded=D("0.00"), units=3
    )
    assert amount == D("10.00")