# Import every model so that Base.metadata (and string-based relationships) see them all.
from app.models.category import Category
from app.models.customer import Customer
from app.models.inventory_movement import InventoryMovement
from app.models.payment import Payment
from app.models.product import Product
from app.models.receipt import Receipt
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.supplier import Supplier
from app.models.user import User

__all__ = [
    "Category",
    "Customer",
    "InventoryMovement",
    "Payment",
    "Product",
    "Receipt",
    "Sale",
    "SaleItem",
    "Supplier",
    "User",
]