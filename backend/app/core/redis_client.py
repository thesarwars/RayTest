"""Redis client singleton + stock-buffer helpers."""

from __future__ import annotations

import redis.asyncio as redis

from app.config import settings

_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Return a shared async Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# ─── Stock buffer keys ────────────────────────────────────────────────

def _stock_key(product_id: str) -> str:
    return f"stock:{product_id}"


def _reservation_zset() -> str:
    return "reservations:expiry"


async def init_stock(product_id: str, quantity: int) -> None:
    """Seed Redis with the current available inventory for a product."""
    r = await get_redis()
    await r.set(_stock_key(product_id), quantity)


async def atomic_decrement_stock(product_id: str, quantity: int) -> int:
    """
    Atomically decrement stock in Redis using DECRBY.
    Returns the new value.  If < 0, rollback and raise.
    """
    r = await get_redis()
    new_val = await r.decrby(_stock_key(product_id), quantity)
    if new_val < 0:
        # Rollback – put the quantity back
        await r.incrby(_stock_key(product_id), quantity)
        return -1  # signal: insufficient stock
    return new_val


async def restore_stock(product_id: str, quantity: int) -> None:
    """Return stock to the Redis buffer (on expiration / cancellation)."""
    r = await get_redis()
    await r.incrby(_stock_key(product_id), quantity)


# ─── Reservation expiry sorted set ───────────────────────────────────

async def register_reservation_expiry(reservation_id: str, expires_at_ts: float) -> None:
    """Add reservation to the ZSET scored by its expiration timestamp."""
    r = await get_redis()
    await r.zadd(_reservation_zset(), {reservation_id: expires_at_ts})


async def pop_expired_reservations(now_ts: float, batch_size: int = 100) -> list[str]:
    """
    Atomically pop reservations whose score (expires_at) <= now_ts.
    Uses ZPOPMIN-style scan to avoid race between multiple workers.
    """
    r = await get_redis()
    # ZRANGEBYSCORE + ZREM in a pipeline for atomicity
    async with r.pipeline(transaction=True) as pipe:
        pipe.zrangebyscore(_reservation_zset(), "-inf", now_ts, start=0, num=batch_size)
        results = await pipe.execute()

    expired_ids: list[str] = results[0] if results else []
    if expired_ids:
        await r.zrem(_reservation_zset(), *expired_ids)
    return expired_ids
