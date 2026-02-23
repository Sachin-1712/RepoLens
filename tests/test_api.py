import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    """GET /api/v1/health should return healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data


def test_root_redirect(client):
    """GET / should return welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "CodeQuery" in data["message"]


def test_create_repository_invalid_url(client):
    """POST /api/v1/repositories with non-GitHub URL should fail."""
    response = client.post(
        "/api/v1/repositories",
        json={
            "repo_url": "https://gitlab.com/user/repo",
            "branch": "main",
        },
    )
    assert response.status_code == 422  # Validation error


def test_create_repository_missing_url(client):
    """POST /api/v1/repositories without repo_url should fail."""
    response = client.post(
        "/api/v1/repositories",
        json={"branch": "main"},
    )
    assert response.status_code == 422


def test_get_repository_not_found(client):
    """GET /api/v1/repositories/99999 should return 404."""
    response = client.get("/api/v1/repositories/99999")
    assert response.status_code == 404


def test_delete_repository_not_found(client):
    """DELETE /api/v1/repositories/99999 should return 404."""
    response = client.delete("/api/v1/repositories/99999")
    assert response.status_code == 404


def test_list_repositories(client):
    """GET /api/v1/repositories should return a list."""
    response = client.get("/api/v1/repositories")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "repositories" in data
    assert isinstance(data["repositories"], list)

def test_update_repository_not_found(client):
    """PUT /api/v1/repositories/99999 should return 404."""
    response = client.put(
        "/api/v1/repositories/99999",
        json={"action": "reanalyze"}
    )
    assert response.status_code == 404
