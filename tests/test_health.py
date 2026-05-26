"""Health endpoint tests."""

from httpx import AsyncClient, Response

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient) -> None:
    """Health endpoint should return 200 with ok status."""
    response: Response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint_content_type(client: AsyncClient) -> None:
    """Health endpoint should return JSON."""
    response: Response = await client.get("/health")

    assert "application/json" in response.headers["content-type"]
