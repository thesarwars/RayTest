"""Product listing service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.product_repo import ProductRepository


class ProductService:
    def __init__(self, db: AsyncSession):
        self.repo = ProductRepository(db)

    async def list_available(self) -> list:
        return await self.repo.list_available()

    async def get(self, product_id: UUID):
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)
        return product
