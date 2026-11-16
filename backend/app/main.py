import os
import sys
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .database.migrations import initialize_database
from .database.backup import auto_backup_on_startup, auto_backup_on_shutdown
from .database.connection import check_database_integrity
from .routers import auth, products, farmers, billing, dashboard, outstanding, reports, notifications, ca_export

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '..', 'app.log'))
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app):
    """Application startup and shutdown lifecycle."""
    logger.info("=== Adinath Agri Services Starting ===")
    
    # Check database integrity before starting
    is_valid, message = check_database_integrity()
    if not is_valid:
        logger.error(f"Database integrity check failed: {message}")
        logger.error("Please restore from backup or contact support")
        raise RuntimeError(f"Database corrupted: {message}")
    
    logger.info("Database integrity check passed")
    
    # Initialize database schema
    try:
        initialize_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Create startup backup
    backup_path = auto_backup_on_startup()
    if backup_path:
        logger.info(f"Startup backup created: {backup_path}")
    else:
        logger.warning("Failed to create startup backup")
    
    logger.info("Application ready to serve requests")
    
    yield
    
    # Shutdown: create backup
    logger.info("=== Adinath Agri Services Shutting Down ===")
    backup_path = auto_backup_on_shutdown()
    if backup_path:
        logger.info(f"Shutdown backup created: {backup_path}")
    else:
        logger.warning("Failed to create shutdown backup")

app = FastAPI(
    title="Adinath Agri Services API",
    description="Backend for the Adinath Agri Services billing & inventory platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the frontend to call the API. Since the frontend is served by this
# same app (see below), this is mostly relevant if you ever split them
# across two different hosts/ports during development.
app.add_middleware(
    CORSMiddleware,
    # Same-origin is the default.  Comma-separated origins can be supplied for
    # a separately hosted frontend, e.g. https://app.example.com.
    allow_origins=[origin.strip() for origin in os.getenv("ADINATH_CORS_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Add inexpensive baseline browser protections to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", str(uuid4()))
    return response

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(farmers.router)
app.include_router(billing.router)
app.include_router(dashboard.router)
app.include_router(outstanding.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(ca_export.router)


# ---------------------------------------------------------------------
# FRONTEND — served from the sibling /frontend folder.
# CSS/JS are mounted at /static; the HTML page is served at "/".
# Resolved as an absolute path so it works no matter where you launch
# the app from (double-clicking, a different terminal cwd, etc.).
# ---------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
# The desktop launcher supplies this path when running from source.  The
# packaged backend uses PyInstaller's temporary resource directory.  Keeping
# this configurable means the same API continues to serve the exact existing
# frontend in browser, development, and installed-desktop modes.
FRONTEND_DIR = os.path.abspath(os.getenv(
    "ADINATH_FRONTEND_DIR",
    os.path.join(getattr(sys, "_MEIPASS", PROJECT_ROOT), "frontend"),
))

if os.path.isdir(FRONTEND_DIR):
    PWA_ASSETS = {
        "manifest.webmanifest": ("manifest.json", "application/manifest+json"),
        "favicon.ico": ("favicon.ico", "image/x-icon"),
        "offline.html": ("offline.html", "text/html"),
    }
    PWA_ICONS = {
        "adinath-agri-logo.svg": "adinath-agri-logo.svg",
        "icon-192.png": "icon-192.png",
        "icon-512.png": "icon-512.png",
        "icon-512-maskable.png": "icon-512-maskable.png",
        "apple-touch-icon.png": "apple-touch-icon.png",
    }

    @app.get("/manifest.webmanifest", include_in_schema=False)
    @app.get("/favicon.ico", include_in_schema=False)
    @app.get("/offline.html", include_in_schema=False)
    def serve_pwa_asset(request: Request):
        """Expose PWA discovery files at the origin root."""
        asset = PWA_ASSETS.get(request.url.path.lstrip("/"))
        if not asset:
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        return FileResponse(os.path.join(FRONTEND_DIR, asset[0]), media_type=asset[1])

    @app.get("/icons/{icon_name}", include_in_schema=False)
    def serve_pwa_icon(icon_name: str):
        """Only serve the allow-listed public PWA icon assets."""
        filename = PWA_ICONS.get(icon_name)
        if not filename:
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        media_type = "image/svg+xml" if filename.endswith(".svg") else "image/png"
        return FileResponse(os.path.join(FRONTEND_DIR, "icons", filename), media_type=media_type)

    app.mount(
        "/static",
        StaticFiles(directory=FRONTEND_DIR),
        name="static",
    )

    @app.get("/service-worker.js", include_in_schema=False)
    def serve_service_worker():
        """Serve the worker at the origin root so it controls the installed app."""
        return FileResponse(
            os.path.join(FRONTEND_DIR, "service-worker.js"),
            media_type="application/javascript",
        )

    @app.get("/", tags=["Frontend"])
    def serve_frontend():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if not os.path.isfile(index_path):
            return JSONResponse(
                status_code=500,
                content={"detail": f"index.html not found at {index_path}"},
            )
        return FileResponse(index_path)
else:
    @app.get("/", tags=["Health"])
    def root():
        return {
            "status": "ok",
            "service": "Adinath Agri Services API",
            "note": f"Frontend folder not found at {FRONTEND_DIR} — API-only mode.",
        }


@app.get("/api/health", tags=["Health"])
def health():
    """Comprehensive health check including database connectivity."""
    try:
        from .database.connection import check_database_integrity
        is_valid, message = check_database_integrity()
        
        return {
            "status": "healthy" if is_valid else "degraded",
            "service": "Adinath Agri Services API",
            "database": "connected" if is_valid else "error",
            "message": message
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "Adinath Agri Services API",
                "error": str(e)
            }
        )
