"""Data-access layer for products."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return await self.db.get(Product, product_id)

    async def list_available(self) -> list[Product]:
        result = await self.db.execute(
            select(Product).where(Product.available_inventory > 0)
        )
        return list(result.scalars().all())

    async def atomic_decrement(self, product_id: UUID, quantity: int) -> bool:
        """
        Atomically reduce available_inventory using an UPDATE … WHERE guard.

        Returns True on success, False if insufficient stock.  The WHERE
        clause ``available_inventory >= :quantity`` prevents overselling at
        the DB level — two concurrent transactions cannot both succeed for
        the last item.
        """
        result = await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .where(Product.available_inventory >= quantity)
            .values(available_inventory=Product.available_inventory - quantity)
        )
        return result.rowcount > 0

    async def restore_inventory(self, product_id: UUID, quantity: int) -> None:
        """Return reserved stock (expiration / cancellation)."""
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(available_inventory=Product.available_inventory + quantity)
        )

    async def finalize_inventory(self, product_id: UUID, quantity: int) -> None:
        """On checkout: reduce total_inventory to match the completed sale."""
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(total_inventory=Product.total_inventory - quantity)
        )
