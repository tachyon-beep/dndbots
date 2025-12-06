"""FastAPI admin server for DnDBots."""

from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from dndbots.admin.plugin import AdminPlugin

# Path to static files (built Vue app)
STATIC_DIR = Path(__file__).parent / "static"

# Shared AdminPlugin instance
_admin_plugin = AdminPlugin()


def get_admin_plugin() -> AdminPlugin:
    """Get the shared AdminPlugin instance."""
    return _admin_plugin


class StopMode(str, Enum):
    """Shutdown modes."""

    CLEAN = "clean"
    FAST = "fast"


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

    @app.post("/api/campaigns/{campaign_id}/start")
    async def start_campaign(campaign_id: str):
        """Start the game loop for a campaign."""
        # TODO: Look up campaign in database
        # For now, return 404 until we wire up storage
        raise HTTPException(status_code=404, detail="Campaign not found")

    @app.post("/api/campaigns/{campaign_id}/stop")
    async def stop_campaign(campaign_id: str, mode: StopMode = StopMode.CLEAN):
        """Stop the running game.

        Args:
            campaign_id: Campaign to stop
            mode: clean (wait for pause) or fast (stop now with checkpoint)
        """
        if not _game_state["running"]:
            raise HTTPException(status_code=400, detail="No game is running")

        if _game_state["campaign_id"] != campaign_id:
            raise HTTPException(
                status_code=400, detail=f"Campaign {campaign_id} is not running"
            )

        # TODO: Implement actual stop logic
        return {"status": "stopping", "mode": mode.value}

    @app.get("/api/entity/{uid}")
    async def get_entity(uid: str):
        """Get entity document from SQLite."""
        # TODO: Query SQLite for entity by UID
        raise HTTPException(status_code=404, detail="Entity not found")

    @app.get("/api/entity/{uid}/relationships")
    async def get_entity_relationships(uid: str):
        """Get entity relationships from Neo4j."""
        # TODO: Query Neo4j for relationships
        raise HTTPException(status_code=404, detail="Entity not found")

    @app.get("/api/search")
    async def search_entities(q: str = ""):
        """Search entities by name or partial UID."""
        if not q:
            return {"results": []}

        # TODO: Search SQLite for matching entities
        return {"results": []}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time event streaming."""
        await websocket.accept()
        _admin_plugin.add_client(websocket)

        try:
            while True:
                data = await websocket.receive_json()

                # Handle ping/pong for connection keepalive
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        finally:
            _admin_plugin.remove_client(websocket)

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
