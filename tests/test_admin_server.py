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


class TestCampaignEndpoints:
    """Tests for campaign API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_list_campaigns_empty(self, client):
        """List campaigns when none exist."""
        response = client.get("/api/campaigns")
        assert response.status_code == 200
        data = response.json()
        assert data["campaigns"] == []

    def test_get_campaign_not_found(self, client):
        """Get non-existent campaign returns 404."""
        response = client.get("/api/campaigns/nonexistent")
        assert response.status_code == 404

    def test_get_state_no_active_game(self, client):
        """Get state when no game is running."""
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
        assert data["campaign_id"] is None
