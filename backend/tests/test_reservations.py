"""Tests for reservation + checkout flow."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_reserve_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/reservations",
        json={"product_id": "00000000-0000-0000-0000-000000000001", "quantity": 1},
    )
    assert resp.status_code == 422 or resp.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
