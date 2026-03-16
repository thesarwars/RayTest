"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import v1_router
from app.config import settings
from app.core.exceptions import AppError
from app.core.middleware import app_error_handler
from app.core import redis_client
from app.worker.stock_sync import sync_stock_once

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown hooks."""
    # ── Startup ──
    logger.info("Syncing product stock counters to Redis …")
    await sync_stock_once()
    yield
    # ── Shutdown ──
    await redis_client.close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)

# Routers
app.include_router(v1_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
