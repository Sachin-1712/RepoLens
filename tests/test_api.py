"""
Tests for Repository CRUD endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    """GET /api/v1/health should return healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data


@pytest.mark.anyio
async def test_root_redirect():
    """GET / should return welcome message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "CodeQuery" in data["message"]


@pytest.mark.anyio
async def test_create_repository_invalid_url():
    """POST /api/v1/repositories with non-GitHub URL should fail."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repositories",
            json={
                "repo_url": "https://gitlab.com/user/repo",
                "branch": "main",
            },
        )
    assert response.status_code == 422  # Validation error


@pytest.mark.anyio
async def test_create_repository_missing_url():
    """POST /api/v1/repositories without repo_url should fail."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repositories",
            json={"branch": "main"},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_repository_not_found():
    """GET /api/v1/repositories/99999 should return 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/repositories/99999")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_repository_not_found():
    """DELETE /api/v1/repositories/99999 should return 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/v1/repositories/99999")
    assert response.status_code == 404
