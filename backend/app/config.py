"""Centralised application settings loaded from environment / .env file."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────
    APP_NAME: str = "inventory-reservation-system"
    DEBUG: bool = False

    # ── Postgres ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://inventory:inventory_secret@postgres:5432/inventory_db"

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── JWT ──────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE-ME-TO-A-REAL-SECRET-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # ── Reservation ──────────────────────────────────────────────
    RESERVATION_TTL_SECONDS: int = 300  # 5 minutes

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
