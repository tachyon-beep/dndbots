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


class TestControlEndpoints:
    """Tests for game control endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_start_campaign_not_found(self, client):
        """Start non-existent campaign returns 404."""
        response = client.post("/api/campaigns/nonexistent/start")
        assert response.status_code == 404

    def test_stop_no_game_running(self, client):
        """Stop when no game running returns 400."""
        response = client.post("/api/campaigns/test/stop")
        assert response.status_code == 400
        data = response.json()
        assert "running" in data["detail"].lower()

    def test_stop_mode_parameter(self, client):
        """Stop accepts mode parameter."""
        # Even though it will fail (no game), it should accept the parameter
        response = client.post("/api/campaigns/test/stop?mode=clean")
        assert response.status_code == 400  # No game running, but mode accepted

        response = client.post("/api/campaigns/test/stop?mode=fast")
        assert response.status_code == 400  # No game running, but mode accepted
