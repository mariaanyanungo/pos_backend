"""Pure pricing/tax/rounding rules - no database, no HTTP.

Conventions
-----------
* Every amount is a Decimal rounded to 2 places, ROUND_HALF_UP.
* Tax is calculated PER LINE on the discounted amount and rounded per line, so a
  receipt's lines always add up exactly to its totals.
* `prices_include_tax=False` (US style):  total = gross - discount + tax
* `prices_include_tax=True`  (VAT style): total = gross - discount, tax is the part of it that is VAT
"""
from dataclasses import dataclass
from decimal import Decimal

from app.core.money import ZERO, money, to_decimal


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class LineAmounts:
    gross: Decimal     
    discount: Decimal
    tax: Decimal
    total: Decimal     


def calculate_line(
    unit_price,
    quantity: int,
    tax_rate,
    *,
    discount_amount=None,
    discount_percent=None,
    prices_include_tax: bool = False,
) -> LineAmounts:
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise PricingError("Quantity must be a positive integer")

    unit_price = to_decimal(unit_price)
    if unit_price < 0:
        raise PricingError("Unit price cannot be negative")

    tax_rate = to_decimal(tax_rate)
    if not Decimal(0) <= tax_rate <= Decimal(100):
        raise PricingError("Tax rate must be between 0 and 100")

    gross = money(unit_price * quantity)

    if discount_percent is not None:
        percent = to_decimal(discount_percent)
        if not Decimal(0) <= percent <= Decimal(100):
            raise PricingError("Discount percent must be between 0 and 100")
        discount = money(gross * percent / Decimal(100))
    elif discount_amount is not None:
        discount = money(discount_amount)
        if discount < 0:
            raise PricingError("Discount cannot be negative")
    else:
        discount = ZERO

    if discount > gross:
        raise PricingError("Discount cannot exceed the line amount")

    taxable = gross - discount
    rate = tax_rate / Decimal(100)

    if prices_include_tax:
        tax = money(taxable - taxable / (Decimal(1) + rate))
        total = taxable
    else:
        tax = money(taxable * rate)
        total = taxable + tax

    return LineAmounts(gross=gross, discount=discount, tax=tax, total=money(total))


def apply_line_pricing(item, prices_include_tax: bool) -> None:
    """(Re)computes the money fields of a SaleItem from its snapshot fields."""
    percent_mode = item.discount_percent is not None
    amounts = calculate_line(
        item.unit_price,
        item.quantity,
        item.tax_rate,
        discount_percent=item.discount_percent if percent_mode else None,
        discount_amount=None if percent_mode else (item.discount_amount or ZERO),
        prices_include_tax=prices_include_tax,
    )
    item.line_subtotal = amounts.gross
    item.discount_amount = amounts.discount
    item.tax_amount = amounts.tax
    item.line_total = amounts.total


def recalculate_sale(sale) -> None:
    """Reprices every line and refreshes the sale totals."""
    subtotal = discount_total = tax_total = total = ZERO
    for item in sale.items:
        apply_line_pricing(item, sale.prices_include_tax)
        subtotal += item.line_subtotal
        discount_total += item.discount_amount
        tax_total += item.tax_amount
        total += item.line_total
    sale.subtotal = money(subtotal)
    sale.discount_total = money(discount_total)
    sale.tax_total = money(tax_total)
    sale.total_amount = money(total)


def refund_amount_for_units(
    *,
    line_total,
    quantity: int,
    units_already_returned: int,
    amount_already_refunded,
    units: int,
) -> Decimal:
    """Refund for returning `units` of a line.

    Proportional and rounded, except that the LAST unit returned takes whatever
    is left of the line, so partial refunds add up to exactly the amount paid
    (no lost or invented cents).
    """
    line_total = money(line_total)
    already = money(amount_already_refunded)
    remaining_amount = line_total - already
    if units_already_returned + units >= quantity:
        return remaining_amount
    proportional = money(line_total * units / quantity)
    return min(proportional, remaining_amount)