"""FastAPI admin server for DnDBots."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Path to static files (built Vue app)
STATIC_DIR = Path(__file__).parent / "static"


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
