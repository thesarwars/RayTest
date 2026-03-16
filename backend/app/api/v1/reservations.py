"""Reservation routes – JWT-protected."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.reservations import (
    CheckoutResponse,
    ReservationResponse,
    ReserveRequest,
)
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    body: ReserveRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Reserve stock for a product.

    Strategy:
      1. Redis DECRBY (instant, atomic, in-memory) – rejects if stock < 0
      2. Postgres UPDATE … WHERE available_inventory >= qty – belt-and-suspenders
      3. Insert reservation row (status=reserved, expires_at=now+5min)
      4. Register expiry in Redis ZSET

    Returns 201 with reservation details, or 409 if out of stock.
    """
    svc = ReservationService(db)
    result = await svc.reserve(user_id, UUID(body.product_id), body.quantity)
    return ReservationResponse(**result)


@router.get("", response_model=list[ReservationResponse])
async def list_my_reservations(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    svc = ReservationService(db)
    return await svc.list_mine(user_id)


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    svc = ReservationService(db)
    result = await svc.get(reservation_id, user_id)
    return ReservationResponse(**result)


@router.post("/{reservation_id}/checkout", response_model=CheckoutResponse)
async def checkout_reservation(
    reservation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Convert a 'reserved' reservation to 'completed'.

    This finalises the sale:
      - Reservation status → completed
      - total_inventory is decremented (the item is sold)
      - The reservation is removed from the expiry ZSET
    """
    svc = ReservationService(db)
    result = await svc.checkout(reservation_id, user_id)
    return CheckoutResponse(**result)
