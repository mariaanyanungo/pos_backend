"""Money helpers.

All monetary values are `Decimal` quantised to 2 places with ROUND_HALF_UP,
which is what receipts/tax authorities expect (0.025 -> 0.03, never 0.02).
Floats are never used for arithmetic.
"""

from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")
ZERO = Decimal("0.00")


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def money(value) -> Decimal:
    return to_decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
