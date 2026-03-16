"""
Expiration Worker – monitors the Redis ZSET and expires stale reservations.

Strategy (avoids full DB scans):
  - Reservations are registered in a Redis Sorted Set with score = expires_at
    timestamp.
  - Every tick the worker calls ZRANGEBYSCORE(-inf, now) to pull only the
    reservations that have *actually* expired.
  - For each expired reservation:
      1. Transition status reserved → expired  (Postgres, with WHERE guard)
      2. Restore available_inventory in Postgres
      3. Restore stock counter in Redis
  - The WHERE guard in step 1 ensures idempotency: if a checkout already
    claimed the reservation, ``mark_expired`` returns None and we skip.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core import redis_client
from app.db.session import async_session_factory
from app.repositories.product_repo import ProductRepository
from app.repositories.reservation_repo import ReservationRepository

logger = logging.getLogger("worker.expiration")

TICK_INTERVAL_SECONDS = 2  # How often the worker polls the ZSET
BATCH_SIZE = 200


async def expire_reservations_tick() -> int:
    """Run one sweep.  Returns number of reservations expired."""
    now_ts = datetime.now(timezone.utc).timestamp()
    expired_ids = await redis_client.pop_expired_reservations(now_ts, batch_size=BATCH_SIZE)

    if not expired_ids:
        return 0

    count = 0
    async with async_session_factory() as db:
        res_repo = ReservationRepository(db)
        prod_repo = ProductRepository(db)

        for rid_str in expired_ids:
            rid = UUID(rid_str)
            reservation = await res_repo.mark_expired(rid)
            if reservation is None:
                # Already completed or cancelled – nothing to restore
                continue

            # Restore Postgres available_inventory
            await prod_repo.restore_inventory(reservation.product_id, reservation.quantity)
            # Restore Redis stock counter
            await redis_client.restore_stock(str(reservation.product_id), reservation.quantity)

            count += 1
            logger.info("Expired reservation %s  (product=%s, qty=%d)",
                        rid, reservation.product_id, reservation.quantity)

        await db.commit()

    return count


async def run_expiration_loop() -> None:
    """Infinite async loop that runs the expiration sweep every tick."""
    logger.info("Expiration worker started (tick=%ds)", TICK_INTERVAL_SECONDS)
    while True:
        try:
            expired = await expire_reservations_tick()
            if expired:
                logger.info("Expired %d reservations this tick", expired)
        except Exception:
            logger.exception("Error in expiration worker tick")
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
