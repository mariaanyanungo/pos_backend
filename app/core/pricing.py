from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from app.core.enums import DiscountType, TaxMode
from app.core.money import (
    ZERO,
    MoneyInput,
    allocate,
    calculate_tax,
    discount_amount,
    parse_money,
    tax_from_inclusive,
    to_decimal,
)


@dataclass(frozen=True)
class ModifierInput:
    """An add-on such as extra cheese or a warranty.

    `price` is charged per unit of the item; `quantity` is how many of this
    modifier each unit of the item carries.
    """

    name: str
    price: MoneyInput
    quantity: int = 1


@dataclass(frozen=True)
class DiscountInput:
    discount_type: DiscountType | str
    value: MoneyInput


@dataclass(frozen=True)
class LineInput:
    line_id: str
    unit_price: MoneyInput
    quantity: int
    tax_rate: MoneyInput = Decimal("0")
    tax_mode: TaxMode | str = TaxMode.EXCLUSIVE
    modifiers: tuple[ModifierInput, ...] = ()
    discount: DiscountInput | None = None


@dataclass(frozen=True)
class LineResult:
    line_id: str
    quantity: int
    unit_price: Decimal
    modifiers_total: Decimal
    gross: Decimal
    line_discount: Decimal
    cart_discount_share: Decimal
    discounted: Decimal  
    tax_rate: Decimal
    tax_mode: TaxMode
    tax: Decimal
    total: Decimal 


@dataclass(frozen=True)
class TaxBreakdownEntry:
    rate: Decimal
    taxable: Decimal  
    tax: Decimal


@dataclass(frozen=True)
class CartResult:
    lines: tuple[LineResult, ...]
    subtotal: Decimal 
    line_discount_total: Decimal
    cart_discount_total: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    tax_breakdown: tuple[TaxBreakdownEntry, ...]


@dataclass(frozen=True)
class _PreparedLine:
    line_id: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    tax_mode: TaxMode
    modifiers_total: Decimal
    gross: Decimal
    line_discount: Decimal
    after_line_discount: Decimal


def _require_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a whole number of at least 1.")
    return value


def _modifiers_per_unit(modifiers: Sequence[ModifierInput]) -> Decimal:
    total = ZERO
    for modifier in modifiers:
        price = parse_money(modifier.price)
        if price < 0:
            raise ValueError("Modifier price cannot be negative.")
        quantity = _require_positive_int(modifier.quantity, "Modifier quantity")
        total += price * quantity
    return total


def _prepare_line(line: LineInput) -> _PreparedLine:
    quantity = _require_positive_int(line.quantity, "Quantity")
    unit_price = parse_money(line.unit_price)
    if unit_price < 0:
        raise ValueError("Unit price cannot be negative.")
    tax_mode = TaxMode(line.tax_mode)
    tax_rate = to_decimal(line.tax_rate)

    modifiers_total = _modifiers_per_unit(line.modifiers) * quantity
    gross = unit_price * quantity + modifiers_total

    if line.discount is None:
        line_discount = ZERO
    else:
        line_discount = discount_amount(
            gross, line.discount.discount_type, line.discount.value
        )

    return _PreparedLine(
        line_id=line.line_id,
        quantity=quantity,
        unit_price=unit_price,
        tax_rate=tax_rate,
        tax_mode=tax_mode,
        modifiers_total=modifiers_total,
        gross=gross,
        line_discount=line_discount,
        after_line_discount=gross - line_discount,
    )


def price_cart(
    lines: Sequence[LineInput],
    cart_discount: DiscountInput | None = None,
) -> CartResult:
    """Price a cart: modifiers, line discounts, cart discount, tax and totals.

    Pure and deterministic. Raises ValueError (or TypeError for floats) on
    invalid input; callers translate that into an HTTP 422.
    """
    prepared = [_prepare_line(line) for line in lines]
    after_line_amounts = [item.after_line_discount for item in prepared]
    after_line_total = sum(after_line_amounts, ZERO)

    if cart_discount is None:
        cart_discount_total = ZERO
    else:
        cart_discount_total = discount_amount(
            after_line_total, cart_discount.discount_type, cart_discount.value
        )

    shares = allocate(cart_discount_total, after_line_amounts)

    results: list[LineResult] = []
    breakdown: dict[Decimal, list[Decimal]] = {}

    for item, share in zip(prepared, shares):
        discounted = item.after_line_discount - share

        if item.tax_mode == TaxMode.EXCLUSIVE:
            tax = calculate_tax(discounted, item.tax_rate)
            total = discounted + tax
            taxable = discounted
        else:
            tax = tax_from_inclusive(discounted, item.tax_rate)
            total = discounted
            taxable = discounted - tax

        results.append(
            LineResult(
                line_id=item.line_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                modifiers_total=item.modifiers_total,
                gross=item.gross,
                line_discount=item.line_discount,
                cart_discount_share=share,
                discounted=discounted,
                tax_rate=item.tax_rate,
                tax_mode=item.tax_mode,
                tax=tax,
                total=total,
            )
        )

        bucket = breakdown.setdefault(item.tax_rate, [ZERO, ZERO])
        bucket[0] += taxable
        bucket[1] += tax

    line_discount_total = sum((r.line_discount for r in results), ZERO)

    return CartResult(
        lines=tuple(results),
        subtotal=sum((r.gross for r in results), ZERO),
        line_discount_total=line_discount_total,
        cart_discount_total=cart_discount_total,
        discount_total=line_discount_total + cart_discount_total,
        tax_total=sum((r.tax for r in results), ZERO),
        total=sum((r.total for r in results), ZERO),
        tax_breakdown=tuple(
            TaxBreakdownEntry(rate=rate, taxable=amounts[0], tax=amounts[1])
            for rate, amounts in sorted(breakdown.items())
        ),
    )