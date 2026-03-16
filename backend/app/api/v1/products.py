"""Product routes – public (no auth required for browsing)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.products import ProductResponse
from app.db.session import get_db
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_db)):
    svc = ProductService(db)
    products = await svc.list_available()
    return [
        ProductResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            price=float(p.price),
            total_inventory=p.total_inventory,
            available_inventory=p.available_inventory,
        )
        for p in products
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = ProductService(db)
    p = await svc.get(product_id)
    return ProductResponse(
        id=str(p.id),
        name=p.name,
        description=p.description,
        price=float(p.price),
        total_inventory=p.total_inventory,
        available_inventory=p.available_inventory,
    )
