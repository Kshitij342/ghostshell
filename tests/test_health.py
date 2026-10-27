"""Tests for the GhostShell health check endpoint."""


def test_health_endpoint(client):
    """Test that /api/health returns HTTP 200 with appropriate app metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "GhostShell"
    assert "tagline" in data
    assert "version" in data
    assert "timestamp" in data
