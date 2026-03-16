"""Tests for the auth endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_returns_token(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "flash@test.com", "password": "str0ngP@ss!"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexist@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401
