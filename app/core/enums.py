from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"


class SaleStatus(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"
    VOIDED = "voided"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"


class StockReason(str, Enum):
    INITIAL = "initial_stock"
    SALE = "sale"
    VOID = "void"
    RETURN = "return"
    RESTOCK = "restock"
    ADJUSTMENT = "adjustment"
    DAMAGE = "damage"
