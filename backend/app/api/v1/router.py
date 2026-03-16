"""Aggregate all v1 routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.reservations import router as reservations_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(products_router)
v1_router.include_router(reservations_router)
