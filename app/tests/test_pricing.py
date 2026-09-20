import random
from decimal import Decimal

import pytest

from app.core.enums import DiscountType, TaxMode
from app.core.money import from_cents, to_cents
from app.core.pricing import (
    DiscountInput,
    LineInput,
    ModifierInput,
    price_cart,
)


def make_line(line_id="A", unit_price="10.00", quantity=1, **kwargs):
    return LineInput(line_id=line_id, unit_price=unit_price, quantity=quantity, **kwargs)


def percent(value):
    return DiscountInput(DiscountType.PERCENTAGE, value)


def fixed(value):
    return DiscountInput(DiscountType.FIXED, value)


def test_simple_line_with_exclusive_tax():
    result = price_cart([make_line(unit_price="10.00", quantity=2, tax_rate="0.20")])
    line = result.lines[0]
    assert line.line_id == "A"
    assert line.quantity == 2
    assert line.unit_price == Decimal("10.00")
    assert line.gross == Decimal("20.00")
    assert line.discounted == Decimal("20.00")
    assert line.tax == Decimal("4.00")
    assert line.total == Decimal("24.00")
    assert result.subtotal == Decimal("20.00")
    assert result.discount_total == Decimal("0.00")
    assert result.tax_total == Decimal("4.00")
    assert result.total == Decimal("24.00")


def test_line_without_tax_rate_defaults_to_untaxed():
    result = price_cart([make_line(unit_price="10.00")])
    assert result.lines[0].tax == Decimal("0.00")
    assert result.total == Decimal("10.00")


def test_result_amounts_always_have_two_decimal_places():
    result = price_cart([make_line(unit_price="3", quantity=3, tax_rate="0.2")])
    for value in (result.subtotal, result.tax_total, result.total):
        assert value.as_tuple().exponent == -2
    assert str(result.total) == "10.80"


def test_multiple_lines_are_summed():
    result = price_cart(
        [
            make_line("A", unit_price="10.00", quantity=1, tax_rate="0.20"),
            make_line("B", unit_price="5.00", quantity=3, tax_rate="0.20"),
        ]
    )
    assert result.subtotal == Decimal("25.00")
    assert result.tax_total == Decimal("5.00")
    assert result.total == Decimal("30.00")


def test_empty_cart_prices_to_zero():
    result = price_cart([])
    assert result.lines == ()
    assert result.subtotal == Decimal("0.00")
    assert result.total == Decimal("0.00")
    assert result.tax_total == Decimal("0.00")
    assert result.tax_breakdown == ()


def test_free_item_is_allowed():
    result = price_cart([make_line(unit_price="0.00", quantity=2, tax_rate="0.20")])
    assert result.total == Decimal("0.00")


def test_modifiers_are_charged_per_unit_of_the_item():
    line = make_line(
        unit_price="8.00",
        quantity=2,
        tax_rate="0.10",
        modifiers=(
            ModifierInput("Extra cheese", "0.75"),
            ModifierInput("Bacon", "1.25", 2),
        ),
    )
    result = price_cart([line])
    priced = result.lines[0]
    assert priced.modifiers_total == Decimal("6.50")
    assert priced.gross == Decimal("22.50")
    assert priced.tax == Decimal("2.25")
    assert priced.total == Decimal("24.75")


def test_line_discount_applies_to_modifiers_too():
    line = make_line(
        unit_price="8.00",
        quantity=2,
        tax_rate="0.10",
        modifiers=(
            ModifierInput("Extra cheese", "0.75"),
            ModifierInput("Bacon", "1.25", 2),
        ),
        discount=percent("10"),
    )
    priced = price_cart([line]).lines[0]
    assert priced.gross == Decimal("22.50")
    assert priced.line_discount == Decimal("2.25")
    assert priced.discounted == Decimal("20.25")
    assert priced.tax == Decimal("2.03")
    assert priced.total == Decimal("22.28")


def test_free_modifier_is_allowed():
    line = make_line(unit_price="5.00", modifiers=(ModifierInput("No onions", "0.00"),))
    assert price_cart([line]).total == Decimal("5.00")


def test_line_percentage_discount():
    line = make_line(unit_price="10.00", quantity=2, tax_rate="0.20", discount=percent("10"))
    priced = price_cart([line]).lines[0]
    assert priced.line_discount == Decimal("2.00")
    assert priced.discounted == Decimal("18.00")
    assert priced.tax == Decimal("3.60")
    assert priced.total == Decimal("21.60")


def test_line_fixed_discount_is_per_line_not_per_unit():
    line = make_line(unit_price="10.00", quantity=2, tax_rate="0.20", discount=fixed("5.00"))
    priced = price_cart([line]).lines[0]
    assert priced.line_discount == Decimal("5.00")
    assert priced.discounted == Decimal("15.00")
    assert priced.tax == Decimal("3.00")
    assert priced.total == Decimal("18.00")


def test_line_discount_accepts_plain_string_type():
    line = make_line(unit_price="10.00", discount=DiscountInput("percentage", "50"))
    assert price_cart([line]).total == Decimal("5.00")


def test_full_line_discount_zeroes_the_line_and_its_tax():
    line = make_line(unit_price="10.00", tax_rate="0.20", discount=percent("100"))
    priced = price_cart([line]).lines[0]
    assert priced.discounted == Decimal("0.00")
    assert priced.tax == Decimal("0.00")
    assert priced.total == Decimal("0.00")



def test_cart_percentage_discount_is_spread_across_lines():
    lines = [
        make_line("A", unit_price="10.00", tax_rate="0.20"),
        make_line("B", unit_price="30.00", tax_rate="0.10"),
    ]
    result = price_cart(lines, cart_discount=percent("10"))

    assert result.cart_discount_total == Decimal("4.00")
    assert [line.cart_discount_share for line in result.lines] == [
        Decimal("1.00"),
        Decimal("3.00"),
    ]
    line_a, line_b = result.lines
    assert line_a.discounted == Decimal("9.00")
    assert line_a.tax == Decimal("1.80")
    assert line_a.total == Decimal("10.80")
    assert line_b.discounted == Decimal("27.00")
    assert line_b.tax == Decimal("2.70")
    assert line_b.total == Decimal("29.70")
    assert result.subtotal == Decimal("40.00")
    assert result.tax_total == Decimal("4.50")
    assert result.total == Decimal("40.50")


def test_cart_fixed_discount_distributes_leftover_cents_exactly():
    lines = [make_line(f"L{i}", unit_price="1.00") for i in range(3)]
    result = price_cart(lines, cart_discount=fixed("1.00"))

    shares = [line.cart_discount_share for line in result.lines]
    assert shares == [Decimal("0.34"), Decimal("0.33"), Decimal("0.33")]
    assert sum(shares) == Decimal("1.00")
    assert [line.discounted for line in result.lines] == [
        Decimal("0.66"),
        Decimal("0.67"),
        Decimal("0.67"),
    ]
    assert result.total == Decimal("2.00")


def test_line_and_cart_discounts_combine():
    lines = [
        make_line("A", unit_price="10.00", discount=percent("50")),
        make_line("B", unit_price="15.00"),
    ]
    result = price_cart(lines, cart_discount=fixed("5.00"))

    assert result.subtotal == Decimal("25.00")
    assert result.line_discount_total == Decimal("5.00")
    assert result.cart_discount_total == Decimal("5.00")
    assert result.discount_total == Decimal("10.00")
    assert [line.cart_discount_share for line in result.lines] == [
        Decimal("1.25"),
        Decimal("3.75"),
    ]
    assert [line.discounted for line in result.lines] == [
        Decimal("3.75"),
        Decimal("11.25"),
    ]
    assert result.total == Decimal("15.00")


def test_full_cart_discount_zeroes_everything():
    lines = [
        make_line("A", unit_price="10.00", tax_rate="0.20"),
        make_line("B", unit_price="30.00", tax_rate="0.10"),
    ]
    result = price_cart(lines, cart_discount=percent("100"))
    assert result.cart_discount_total == Decimal("40.00")
    assert result.tax_total == Decimal("0.00")
    assert result.total == Decimal("0.00")
    assert all(line.total == Decimal("0.00") for line in result.lines)


def test_cart_discount_never_pushes_a_line_below_zero():
    lines = [
        make_line("A", unit_price="0.01"),
        make_line("B", unit_price="0.01"),
        make_line("C", unit_price="0.01"),
    ]
    result = price_cart(lines, cart_discount=fixed("0.03"))
    assert all(line.discounted == Decimal("0.00") for line in result.lines)


def test_zero_cart_discount_changes_nothing():
    result = price_cart([make_line(unit_price="10.00")], cart_discount=fixed("0.00"))
    assert result.cart_discount_total == Decimal("0.00")
    assert result.total == Decimal("10.00")


def test_tax_is_rounded_per_line_not_on_the_total():
    lines = [make_line(f"L{i}", unit_price="0.02", tax_rate="0.20") for i in range(3)]
    result = price_cart(lines)
    assert all(line.tax == Decimal("0.00") for line in result.lines)
    assert result.tax_total == Decimal("0.00")
    assert result.total == Decimal("0.06")


def test_inclusive_tax_does_not_change_the_payable_amount():
    line = make_line(unit_price="12.00", tax_rate="0.20", tax_mode=TaxMode.INCLUSIVE)
    result = price_cart([line])
    priced = result.lines[0]
    assert priced.gross == Decimal("12.00")
    assert priced.tax == Decimal("2.00")
    assert priced.total == Decimal("12.00")
    assert result.total == Decimal("12.00")
    assert result.tax_total == Decimal("2.00")


def test_inclusive_tax_after_a_discount():
    line = make_line(
        unit_price="12.00",
        tax_rate="0.20",
        tax_mode="inclusive",
        discount=percent("10"),
    )
    result = price_cart([line])
    priced = result.lines[0]
    assert priced.discounted == Decimal("10.80")
    assert priced.tax == Decimal("1.80")
    assert priced.total == Decimal("10.80")
    entry = result.tax_breakdown[0]
    assert entry.taxable == Decimal("9.00")
    assert entry.tax == Decimal("1.80")


def test_tax_breakdown_groups_lines_by_rate_in_ascending_order():
    lines = [
        make_line("A", unit_price="10.00", tax_rate="0.20"),
        make_line("B", unit_price="10.00", tax_rate="0.20"),
        make_line("C", unit_price="10.00", tax_rate="0"),
    ]
    result = price_cart(lines)
    assert [(e.rate, e.taxable, e.tax) for e in result.tax_breakdown] == [
        (Decimal("0"), Decimal("10.00"), Decimal("0.00")),
        (Decimal("0.20"), Decimal("20.00"), Decimal("4.00")),
    ]


def test_tax_breakdown_treats_equal_rates_written_differently_as_one_group():
    lines = [
        make_line("A", unit_price="10.00", tax_rate="0.2"),
        make_line("B", unit_price="10.00", tax_rate="0.20"),
    ]
    result = price_cart(lines)
    assert len(result.tax_breakdown) == 1
    assert result.tax_breakdown[0].taxable == Decimal("20.00")


def test_tax_breakdown_for_the_per_line_rounding_case():
    lines = [make_line(f"L{i}", unit_price="0.02", tax_rate="0.20") for i in range(3)]
    entry = price_cart(lines).tax_breakdown[0]
    assert entry.rate == Decimal("0.20")
    assert entry.taxable == Decimal("0.06")
    assert entry.tax == Decimal("0.00")



@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "2", None])
def test_invalid_quantity_is_rejected(quantity):
    with pytest.raises(ValueError):
        price_cart([make_line(quantity=quantity)])


@pytest.mark.parametrize("unit_price", ["-1.00", "10.999"])
def test_invalid_unit_price_is_rejected(unit_price):
    with pytest.raises(ValueError):
        price_cart([make_line(unit_price=unit_price)])


def test_float_unit_price_is_rejected():
    with pytest.raises(TypeError):
        price_cart([make_line(unit_price=10.5)])


@pytest.mark.parametrize("tax_rate", ["1.5", "-0.1"])
def test_invalid_tax_rate_is_rejected(tax_rate):
    with pytest.raises(ValueError):
        price_cart([make_line(tax_rate=tax_rate)])


def test_unknown_tax_mode_is_rejected():
    with pytest.raises(ValueError):
        price_cart([make_line(tax_mode="bogus")])


def test_negative_modifier_price_is_rejected():
    line = make_line(modifiers=(ModifierInput("Refund", "-1.00"),))
    with pytest.raises(ValueError):
        price_cart([line])


@pytest.mark.parametrize("quantity", [0, -1, True])
def test_invalid_modifier_quantity_is_rejected(quantity):
    line = make_line(modifiers=(ModifierInput("Cheese", "1.00", quantity),))
    with pytest.raises(ValueError):
        price_cart([line])


def test_line_fixed_discount_above_gross_is_rejected():
    with pytest.raises(ValueError):
        price_cart([make_line(unit_price="10.00", quantity=2, discount=fixed("25.00"))])


def test_line_percentage_discount_above_100_is_rejected():
    with pytest.raises(ValueError):
        price_cart([make_line(discount=percent("101"))])


def test_cart_fixed_discount_above_subtotal_is_rejected():
    with pytest.raises(ValueError):
        price_cart([make_line(unit_price="10.00")], cart_discount=fixed("10.01"))


def test_cart_discount_on_an_empty_cart_is_rejected():
    with pytest.raises(ValueError):
        price_cart([], cart_discount=fixed("1.00"))


def test_cart_discount_is_measured_after_line_discounts():
    line = make_line(unit_price="10.00", discount=percent("50"))
    with pytest.raises(ValueError):
        price_cart([line], cart_discount=fixed("6.00"))


def random_line(rng, index):
    modifiers = tuple(
        ModifierInput(
            name=f"mod-{j}",
            price=from_cents(rng.randint(0, 500)),
            quantity=rng.randint(1, 3),
        )
        for j in range(rng.randint(0, 3))
    )
    discount = None
    if rng.random() < 0.4:
        discount = percent(Decimal(rng.randint(0, 100)))
    return LineInput(
        line_id=f"L{index}",
        unit_price=from_cents(rng.randint(0, 5000)),
        quantity=rng.randint(1, 5),
        tax_rate=rng.choice(["0", "0.07", "0.20", "0.21"]),
        tax_mode=rng.choice([TaxMode.EXCLUSIVE, TaxMode.INCLUSIVE]),
        modifiers=modifiers,
        discount=discount,
    )


def test_random_carts_keep_every_total_consistent():
    rng = random.Random(2024)
    for _ in range(200):
        lines = [random_line(rng, i) for i in range(rng.randint(1, 6))]

        base = price_cart(lines)
        after_line_discounts = base.subtotal - base.line_discount_total

        choice = rng.random()
        if choice < 0.3:
            cart_discount = None
        elif choice < 0.65:
            cart_discount = percent(Decimal(rng.randint(0, 100)))
        else:
            cart_discount = fixed(from_cents(rng.randint(0, to_cents(after_line_discounts))))

        result = price_cart(lines, cart_discount=cart_discount)

        assert result.total == sum(line.total for line in result.lines)
        assert result.tax_total == sum(line.tax for line in result.lines)
        assert result.cart_discount_total == sum(
            line.cart_discount_share for line in result.lines
        )
        assert result.subtotal - result.discount_total == sum(
            line.discounted for line in result.lines
        )
        assert result.total == sum(
            entry.taxable + entry.tax for entry in result.tax_breakdown
        )

        for line in result.lines:
            assert line.discounted >= 0
            assert line.total >= 0
            assert line.cart_discount_share <= line.gross - line.line_discount
            if line.tax_mode == TaxMode.EXCLUSIVE:
                assert line.total == line.discounted + line.tax
            else:
                assert line.total == line.discounted