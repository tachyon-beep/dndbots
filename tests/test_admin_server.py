"""Tests for admin FastAPI server."""

import pytest
from fastapi.testclient import TestClient

from dndbots.admin.server import create_app


class TestServerBasics:
    """Basic server tests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Health check endpoint works."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_root_returns_html(self, client):
        """Root serves index.html or placeholder."""
        response = client.get("/")
        assert response.status_code == 200
        # Will serve HTML when static files exist
        assert "text/html" in response.headers.get("content-type", "")

    def test_api_prefix(self, client):
        """API routes use /api prefix."""
        response = client.get("/api/health")
        assert response.status_code == 200
