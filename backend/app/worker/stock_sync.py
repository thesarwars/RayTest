"""
Stock Sync Worker – periodically syncs the Redis stock counters with
the Postgres source of truth.

Runs every 60 seconds.  This is a safety net: if Redis drifts (crash,
network partition), this re-seeds the counters from Postgres.
"""

import asyncio
import logging

from sqlalchemy import select

from app.core import redis_client
from app.db.session import async_session_factory
from app.models.product import Product

logger = logging.getLogger("worker.stock_sync")

SYNC_INTERVAL_SECONDS = 60


async def sync_stock_once() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(Product))
        products = result.scalars().all()
        for p in products:
            await redis_client.init_stock(str(p.id), p.available_inventory)
        logger.info("Synced %d product stock counters to Redis", len(products))


async def run_stock_sync_loop() -> None:
    logger.info("Stock-sync worker started (interval=%ds)", SYNC_INTERVAL_SECONDS)
    # Initial sync on startup
    await sync_stock_once()
    while True:
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        try:
            await sync_stock_once()
        except Exception:
            logger.exception("Error in stock sync tick")
