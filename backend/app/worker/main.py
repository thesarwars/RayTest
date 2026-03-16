"""
Worker entry-point – runs the expiration + stock-sync loops concurrently
using asyncio.
"""

import asyncio
import logging

from app.worker.expiration_worker import run_expiration_loop
from app.worker.stock_sync import run_stock_sync_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-6s  %(message)s",
)


async def main() -> None:
    await asyncio.gather(
        run_expiration_loop(),
        run_stock_sync_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
