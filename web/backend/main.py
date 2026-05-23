"""
main.py — FastAPI Application Entry Point

Initializes the FastAPI app, registers all routers, serves the static
frontend, and loads the data service on startup.
"""

from __future__ import annotations

import logging
import os
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.backend.routers import overview, segments, customers, models, pipeline, export, upload
from web.backend.services.data_service import get_data_service
from web.backend.services.ml_service import compute_alive_matrix
from web.backend.schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Resolve project root so src/ imports work from any working directory
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Patch Starlette multipart size limit BEFORE app creation ──────────
# Default max_part_size is 1 MB — raises 400 for any file larger than that.
# Patch to 300 MB to support real retail datasets (UCI ~45 MB CSV).
_MAX_UPLOAD_BYTES = 300 * 1024 * 1024  # 300 MB

try:
    from starlette.formparsers import MultiPartParser
    MultiPartParser.max_part_size = _MAX_UPLOAD_BYTES
    logger.info(f"MultiPartParser.max_part_size patched to {_MAX_UPLOAD_BYTES // 1024 // 1024} MB")
except Exception as _patch_err:
    logger.warning(f"Could not patch MultiPartParser: {_patch_err}")

# ---------------------------------------------------------------------------
# Startup / lifespan
# ---------------------------------------------------------------------------

# Cache for the alive matrix (expensive to compute per-request)
_alive_matrix_cache: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data and pre-compute expensive artifacts on startup."""
    global _alive_matrix_cache

    logger.info("Loading data service...")
    svc = get_data_service()
    svc.load()
    if svc.is_ready():
        logger.info(f"Data service ready. {len(svc.df_segments)} customers loaded.")
    else:
        logger.warning("Data service not ready — run the ML pipeline first.")

    # Pre-compute alive matrix so the endpoint is instant
    logger.info("Pre-computing BG/NBD alive probability matrix...")
    try:
        _alive_matrix_cache = compute_alive_matrix()
        logger.info("Alive matrix cached.")
    except Exception as exc:
        logger.warning(f"Could not pre-compute alive matrix: {exc}")

    yield  # Server runs here

    logger.info("Shutting down CLV Intelligence Platform.")


# Expose cache for the models router
def get_alive_matrix_cache() -> dict:
    return _alive_matrix_cache


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CLV Segmentation API",
    description="REST API for the Customer Lifetime Value Segmentation ML platform.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(overview.router)
app.include_router(segments.router)
app.include_router(customers.router)
app.include_router(models.router)
app.include_router(pipeline.router)
app.include_router(export.router)
app.include_router(upload.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Return API health status."""
    svc = get_data_service()
    return HealthResponse(
        status="ok",
        pipeline_ready=svc.is_ready(),
        data_loaded=svc.df_segments is not None,
    )


# ---------------------------------------------------------------------------
# Static frontend — serve after all API routes
# ---------------------------------------------------------------------------

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index() -> FileResponse:
        """Serve the SPA index.html."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        """Catch-all: serve index.html for client-side routing."""
        # Never intercept API or static routes
        if full_path.startswith("api/") or full_path.startswith("static/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = os.path.join(FRONTEND_DIR, "index.html")
        return FileResponse(index)
