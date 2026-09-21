"""Payment-processor seam.

`CashGateway` and `SimulatedCardGateway` approve everything; they exist so the
whole checkout flow (authorize -> capture -> refund) runs without a real
processor. To go live, implement `PaymentGateway` for your acquirer (Stripe,
Adyen, a terminal SDK...) and register it in GATEWAYS. Tests swap entries in
GATEWAYS to simulate declines.
"""
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class GatewayError(Exception):
    """The processor could not be reached / returned an unusable answer."""


@dataclass(frozen=True)
class GatewayResult:
    approved: bool
    reference: str | None = None
    failure_reason: str | None = None


class PaymentGateway(Protocol):
    def authorize(self, amount: Decimal, idempotency_key: str) -> GatewayResult: ...

    def capture(self, reference: str, amount: Decimal) -> GatewayResult: ...

    def void(self, reference: str) -> GatewayResult: ...

    def refund(self, reference: str | None, amount: Decimal) -> GatewayResult: ...


class CashGateway:
    def authorize(self, amount: Decimal, idempotency_key: str) -> GatewayResult:
        return GatewayResult(approved=True, reference=f"CASH-{uuid.uuid4().hex[:12].upper()}")

    def capture(self, reference: str, amount: Decimal) -> GatewayResult:
        return GatewayResult(approved=True, reference=reference)

    def void(self, reference: str) -> GatewayResult:
        return GatewayResult(approved=True, reference=reference)

    def refund(self, reference: str | None, amount: Decimal) -> GatewayResult:
        return GatewayResult(approved=True, reference=reference)


class SimulatedCardGateway:
    def authorize(self, amount: Decimal, idempotency_key: str) -> GatewayResult:
        return GatewayResult(approved=True, reference=f"CARD-{uuid.uuid4().hex[:12].upper()}")

    def capture(self, reference: str, amount: Decimal) -> GatewayResult:
        return GatewayResult(approved=True, reference=reference)

    def void(self, reference: str) -> GatewayResult:
        return GatewayResult(approved=True, reference=reference)

    def refund(self, reference: str | None, amount: Decimal) -> GatewayResult:
        return GatewayResult(approved=True, reference=reference)


GATEWAYS: dict[str, PaymentGateway] = {
    "cash": CashGateway(),
    "card": SimulatedCardGateway(),
}


def get_gateway(method: str) -> PaymentGateway:
    return GATEWAYS[method]