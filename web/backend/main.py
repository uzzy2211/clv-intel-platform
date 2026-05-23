"""
main.py — FastAPI Application Entry Point

Works whether run from the repo root (locally) or from web/backend (Render).
All imports use package-relative names that resolve correctly in both contexts.
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

# ---------------------------------------------------------------------------
# Path bootstrap — must happen BEFORE any project imports
#
# __file__ is  .../web/backend/main.py  in both environments.
# BACKEND_DIR  = .../web/backend
# WEB_DIR      = .../web
# REPO_ROOT    = .../ (contains src/, data/, models/, config.yaml)
#
# We add REPO_ROOT to sys.path so that `import src.config` works,
# and we add BACKEND_DIR so that `import routers.overview` works
# when Render sets the working directory to web/backend.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))          # web/backend
if os.path.exists(os.path.join(os.path.dirname(BACKEND_DIR), "config.yaml")):
    REPO_ROOT = os.path.dirname(BACKEND_DIR)
else:
    REPO_ROOT = os.path.dirname(os.path.dirname(BACKEND_DIR))         # repo root
WEB_DIR     = os.path.join(REPO_ROOT, "web")                          # web


for _p in (REPO_ROOT, BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Now safe to import project modules
from routers import overview, segments, customers, models, pipeline, export, upload
from services.data_service import get_data_service
from services.ml_service import compute_alive_matrix
from schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Patch Starlette multipart size limit BEFORE app creation ──────────
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

_alive_matrix_cache: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _alive_matrix_cache

    logger.info("Loading data service...")
    svc = get_data_service()
    svc.load()
    if svc.is_ready():
        logger.info(f"Data service ready. {len(svc.df_segments)} customers loaded.")
    else:
        logger.warning("Data service not ready — run the ML pipeline first.")

    logger.info("Pre-computing BG/NBD alive probability matrix...")
    try:
        _alive_matrix_cache = compute_alive_matrix()
        logger.info("Alive matrix cached.")
    except Exception as exc:
        logger.warning(f"Could not pre-compute alive matrix: {exc}")

    yield

    logger.info("Shutting down CLV Intelligence Platform.")


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
    svc = get_data_service()
    return HealthResponse(
        status="ok",
        pipeline_ready=svc.is_ready(),
        data_loaded=svc.df_segments is not None,
    )

# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

FRONTEND_DIR = os.path.join(WEB_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index() -> FileResponse:
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path.startswith("static/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
