"""Data-access layer for reservations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reservation import Reservation, ReservationStatus


class ReservationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: UUID,
        product_id: UUID,
        quantity: int,
        status: ReservationStatus,
        expires_at: datetime | None = None,
    ) -> Reservation:
        reservation = Reservation(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            status=status,
            expires_at=expires_at,
        )
        self.db.add(reservation)
        await self.db.flush()
        return reservation

    async def get_by_id(self, reservation_id: UUID) -> Reservation | None:
        return await self.db.get(Reservation, reservation_id)

    async def get_by_id_and_user(self, reservation_id: UUID, user_id: UUID) -> Reservation | None:
        result = await self.db.execute(
            select(Reservation).where(
                Reservation.id == reservation_id,
                Reservation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_expired(self, reservation_id: UUID) -> Reservation | None:
        """Transition reserved → expired.  Returns None if already transitioned."""
        result = await self.db.execute(
            update(Reservation)
            .where(Reservation.id == reservation_id)
            .where(Reservation.status == ReservationStatus.RESERVED)
            .values(status=ReservationStatus.EXPIRED)
            .returning(Reservation)
        )
        return result.scalar_one_or_none()

    async def mark_completed(self, reservation_id: UUID) -> Reservation | None:
        """Transition reserved → completed."""
        result = await self.db.execute(
            update(Reservation)
            .where(Reservation.id == reservation_id)
            .where(Reservation.status == ReservationStatus.RESERVED)
            .values(status=ReservationStatus.COMPLETED)
            .returning(Reservation)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[Reservation]:
        result = await self.db.execute(
            select(Reservation).where(Reservation.user_id == user_id).order_by(Reservation.created_at.desc())
        )
        return list(result.scalars().all())
