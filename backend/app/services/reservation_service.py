"""
Reservation Service – the heart of the flash-sale concurrency strategy.

Flow (POST /reservations):
  1. Redis DECRBY  → instant in-memory stock guard (prevents thundering herd)
  2. Postgres atomic UPDATE … WHERE available_inventory >= qty → prevents
     double-spend at the DB level (belt-and-suspenders)
  3. Insert reservation row with status='reserved', expires_at = now + 5 min
  4. Register expiry in Redis ZSET for the background worker

Flow (POST /reservations/{id}/checkout):
  1. Transition reservation reserved → completed
  2. Deduct from total_inventory (final sale)

Double-Spend Prevention:
  - Two users requesting the last item both hit Redis DECRBY.  Only the one
    that brings the counter to >= 0 proceeds.  The loser sees < 0 and is
    rejected instantly (Redis single-threaded, DECRBY is atomic).
  - Even if a race slips through (network partition, Redis failover), the
    Postgres WHERE guard ensures the UPDATE affects 0 rows for the loser
    and we rollback the Redis counter.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import InsufficientStockError, NotFoundError, AppError
from app.core import redis_client
from app.models.reservation import ReservationStatus
from app.repositories.product_repo import ProductRepository
from app.repositories.reservation_repo import ReservationRepository


class ReservationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.reservation_repo = ReservationRepository(db)

    # ──────────────────────────────────────────────────────────────
    # Reserve
    # ──────────────────────────────────────────────────────────────
    async def reserve(self, user_id: UUID, product_id: UUID, quantity: int) -> dict:
        # ① Fast-path: Redis atomic decrement (in-memory, single-threaded)
        stock_after = await redis_client.atomic_decrement_stock(str(product_id), quantity)
        if stock_after < 0:
            raise InsufficientStockError(product_id)

        # ② Slow-path: Postgres atomic UPDATE … WHERE guard
        ok = await self.product_repo.atomic_decrement(product_id, quantity)
        if not ok:
            # Redis succeeded but Postgres rejected (edge case) → rollback Redis
            await redis_client.restore_stock(str(product_id), quantity)
            raise InsufficientStockError(product_id)

        # ③ Persist reservation
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.RESERVATION_TTL_SECONDS)
        reservation = await self.reservation_repo.create(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            status=ReservationStatus.RESERVED,
            expires_at=expires_at,
        )

        # ④ Register in Redis ZSET for the expiration worker
        await redis_client.register_reservation_expiry(
            str(reservation.id),
            expires_at.timestamp(),
        )

        return {
            "reservation_id": str(reservation.id),
            "product_id": str(product_id),
            "quantity": quantity,
            "status": reservation.status.value,
            "expires_at": expires_at.isoformat(),
        }

    # ──────────────────────────────────────────────────────────────
    # Checkout (reserved → completed)
    # ──────────────────────────────────────────────────────────────
    async def checkout(self, reservation_id: UUID, user_id: UUID) -> dict:
        reservation = await self.reservation_repo.get_by_id_and_user(reservation_id, user_id)
        if not reservation:
            raise NotFoundError("Reservation", reservation_id)

        if reservation.status == ReservationStatus.EXPIRED:
            raise AppError("Reservation has expired", status_code=410)
        if reservation.status == ReservationStatus.COMPLETED:
            raise AppError("Reservation already completed", status_code=409)
        if reservation.status != ReservationStatus.RESERVED:
            raise AppError(f"Cannot checkout reservation in '{reservation.status.value}' state", status_code=400)

        # Transition reserved → completed
        updated = await self.reservation_repo.mark_completed(reservation_id)
        if not updated:
            raise AppError("Reservation could not be completed (concurrent modification)", status_code=409)

        # Deduct from total_inventory (the item is sold)
        await self.product_repo.finalize_inventory(reservation.product_id, reservation.quantity)

        # Remove from the expiry ZSET (no longer needs expiration)
        r = await redis_client.get_redis()
        await r.zrem(redis_client._reservation_zset(), str(reservation_id))

        return {
            "reservation_id": str(reservation_id),
            "status": "completed",
        }

    # ──────────────────────────────────────────────────────────────
    # Query
    # ──────────────────────────────────────────────────────────────
    async def get(self, reservation_id: UUID, user_id: UUID) -> dict:
        reservation = await self.reservation_repo.get_by_id_and_user(reservation_id, user_id)
        if not reservation:
            raise NotFoundError("Reservation", reservation_id)
        return {
            "reservation_id": str(reservation.id),
            "product_id": str(reservation.product_id),
            "quantity": reservation.quantity,
            "status": reservation.status.value,
            "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,
            "created_at": reservation.created_at.isoformat(),
        }

    async def list_mine(self, user_id: UUID) -> list[dict]:
        reservations = await self.reservation_repo.list_by_user(user_id)
        return [
            {
                "reservation_id": str(r.id),
                "product_id": str(r.product_id),
                "quantity": r.quantity,
                "status": r.status.value,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in reservations
        ]
