"""Tests for the expiration worker logic."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.worker.expiration_worker import expire_reservations_tick


@pytest.mark.asyncio
@patch("app.worker.expiration_worker.redis_client")
async def test_no_expired_returns_zero(mock_redis):
    mock_redis.pop_expired_reservations = AsyncMock(return_value=[])
    count = await expire_reservations_tick()
    assert count == 0
