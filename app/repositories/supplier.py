from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self):
        super().__init__(Supplier)


supplier_repository = SupplierRepository()
