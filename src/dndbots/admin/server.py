"""FastAPI admin server for DnDBots."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Path to static files (built Vue app)
STATIC_DIR = Path(__file__).parent / "static"

# Game state (module-level for simplicity, will be managed properly in Task 8)
_game_state: dict[str, Any] = {
    "running": False,
    "campaign_id": None,
    "game": None,
}


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="DnDBots Admin",
        description="Admin UI for monitoring and controlling DnDBots campaigns",
        version="0.1.0",
    )

    # Health check
    @app.get("/api/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/api/campaigns")
    async def list_campaigns():
        """List all available campaigns."""
        # TODO: Query SQLite for campaigns
        return {"campaigns": []}

    @app.get("/api/campaigns/{campaign_id}")
    async def get_campaign(campaign_id: str):
        """Get campaign details."""
        # TODO: Query SQLite for campaign
        raise HTTPException(status_code=404, detail="Campaign not found")

    @app.get("/api/state")
    async def get_state():
        """Get current game state."""
        return {
            "running": _game_state["running"],
            "campaign_id": _game_state["campaign_id"],
        }

    # Serve Vue SPA
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the Vue SPA index.html."""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return index_path.read_text()
        return """
        <!DOCTYPE html>
        <html>
        <head><title>DnDBots Admin</title></head>
        <body>
            <h1>DnDBots Admin</h1>
            <p>Vue frontend not built yet. Run: <code>cd admin-ui && npm run build</code></p>
        </body>
        </html>
        """

    # Mount static files if they exist
    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    return app


# App instance for uvicorn
app = create_app()
