"""
upload.py — File Upload & Ingest Router

Streams uploaded CSV/XLSX files directly to disk (no full in-memory read),
normalises column names, then triggers the full ML pipeline.

Handles:
- UCI Online Retail II column variants  (Invoice / Price / Customer ID)
- Standard Online Retail variants       (InvoiceNo / UnitPrice / CustomerID)
- latin-1 / UTF-8 / cp1252 encoding detection
- Multi-sheet Excel files               (UCI has two year sheets)
- Files up to 300 MB streamed to disk   (no Starlette body-size limit hit)
- Graceful error reporting with full traceback surfaced to the frontend
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
import traceback
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

# ── Shared in-memory state ─────────────────────────────────────────────
_upload_state: dict = {
    "status":     "idle",   # idle | uploading | processing | done | error
    "filename":   None,
    "rows":       None,
    "message":    "",
    "progress":   0,
    "started_at": None,
}

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE_BYTES = 300 * 1024 * 1024   # 300 MB hard cap
CHUNK_SIZE          = 256 * 1024          # 256 KB streaming chunks


class UploadStatusResponse(BaseModel):
    status:   str
    filename: Optional[str]
    rows:     Optional[int]
    message:  str
    progress: int


def _ext_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a .csv or .xlsx file.",
        )
    return ext


# ── Background processing ──────────────────────────────────────────────

def _process_file(tmp_path: str, ext: str, original_name: str, state: dict) -> None:
    """Validate, normalise, save, and run the full ML pipeline."""

    state["status"]   = "processing"
    state["progress"] = 10
    state["message"]  = "Parsing uploaded file..."

    try:
        from src.data_loader import (
            _normalise_columns,
            _read_csv_robust,
            _read_excel_robust,
            validate_schema,
        )

        # ── 1. Parse file ──────────────────────────────────────────
        state["progress"] = 15
        if ext in (".xlsx", ".xls"):
            state["message"] = "Reading Excel file (may take a moment for large files)..."
            df_raw = _read_excel_robust(tmp_path)
        else:
            state["message"] = "Reading CSV file..."
            df_raw = _read_csv_robust(tmp_path)

        state["progress"] = 25
        logger.info(f"Raw columns from upload: {df_raw.columns.tolist()}")
        state["message"] = f"Loaded {len(df_raw):,} rows. Normalising column names..."

        # ── 2. Normalise + validate ────────────────────────────────
        df_raw = _normalise_columns(df_raw)

        state["progress"] = 30
        state["message"]  = "Validating schema..."
        validate_schema(df_raw)

        state["rows"]     = len(df_raw)
        state["progress"] = 38
        state["message"]  = f"Schema valid ({len(df_raw):,} rows). Saving dataset..."

        # ── 3. Save as active dataset ──────────────────────────────
        dest_path = os.path.join(ROOT, "data", "synthetic", "synthetic_data.csv")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        df_raw.to_csv(dest_path, index=False)
        logger.info(f"Saved {len(df_raw):,} rows → {dest_path}")

        state["progress"] = 45
        state["message"]  = "Dataset saved. Running ML pipeline..."

        # ── 4. Run full ML pipeline ────────────────────────────────
        from web.backend.services.ml_service import run_full_pipeline
        success, message, duration = run_full_pipeline()

        if not success:
            raise RuntimeError(f"ML pipeline failed: {message}")

        state["progress"] = 88
        state["message"]  = "Pipeline complete. Reloading data service..."

        # ── 5. Reload data service ─────────────────────────────────
        from web.backend.services.data_service import get_data_service
        get_data_service().reload()

        # ── 6. Refresh alive matrix cache ──────────────────────────
        state["progress"] = 95
        state["message"]  = "Updating model cache..."
        _refresh_alive_matrix()

        # ── Done ───────────────────────────────────────────────────
        state["status"]   = "done"
        state["progress"] = 100
        state["message"]  = (
            f"Successfully processed {len(df_raw):,} transactions "
            f"in {duration:.1f}s. Dashboard is ready."
        )
        logger.info(f"Upload complete: {original_name} ({len(df_raw):,} rows, {duration:.1f}s)")

    except Exception as exc:
        logger.error(f"Upload processing failed:\n{traceback.format_exc()}")
        state["status"]   = "error"
        state["progress"] = 0
        state["message"]  = str(exc)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _refresh_alive_matrix() -> None:
    """Recompute alive matrix cache — avoids circular import via module reference."""
    try:
        from web.backend.services.ml_service import compute_alive_matrix
        import web.backend.main as _main
        new_cache = compute_alive_matrix()
        _main._alive_matrix_cache.clear()
        _main._alive_matrix_cache.update(new_cache)
        logger.info("Alive matrix cache refreshed.")
    except Exception as exc:
        logger.warning(f"Could not refresh alive matrix: {exc}")


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/file", response_model=UploadStatusResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadStatusResponse:
    """
    Accept a CSV or XLSX transaction file and trigger the ML pipeline.

    Streams the file to a temp path in chunks so the Starlette multipart
    body-size limit is never hit in memory.
    """
    global _upload_state

    if _upload_state["status"] in ("uploading", "processing"):
        raise HTTPException(status_code=409, detail="A file is already being processed.")

    filename = file.filename or "upload.csv"
    ext      = _ext_from_filename(filename)

    # ── Stream to temp file in chunks ─────────────────────────────
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    total_bytes = 0

    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_FILE_SIZE_BYTES:
                tmp.close()
                os.unlink(tmp.name)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"File too large (>{MAX_FILE_SIZE_BYTES // 1024 // 1024} MB). "
                        "Please reduce the dataset size or contact support."
                    ),
                )
            tmp.write(chunk)
    finally:
        tmp.close()

    size_mb = total_bytes / 1024 / 1024
    logger.info(f"Upload received: {filename} ({size_mb:.1f} MB) → {tmp.name}")

    # ── Reset state ────────────────────────────────────────────────
    _upload_state.update({
        "status":     "uploading",
        "filename":   filename,
        "rows":       None,
        "message":    f"File received ({size_mb:.1f} MB). Starting processing...",
        "progress":   5,
        "started_at": time.time(),
    })

    background_tasks.add_task(
        _process_file, tmp.name, ext, filename, _upload_state
    )

    return UploadStatusResponse(
        status   = _upload_state["status"],
        filename = _upload_state["filename"],
        rows     = _upload_state["rows"],
        message  = _upload_state["message"],
        progress = _upload_state["progress"],
    )


@router.get("/status", response_model=UploadStatusResponse)
def get_upload_status() -> UploadStatusResponse:
    """Poll the current upload/processing status."""
    return UploadStatusResponse(
        status   = _upload_state["status"],
        filename = _upload_state["filename"],
        rows     = _upload_state["rows"],
        message  = _upload_state["message"],
        progress = _upload_state["progress"],
    )


@router.post("/reset")
def reset_upload() -> JSONResponse:
    """Reset the upload state back to idle."""
    _upload_state.update({
        "status": "idle", "filename": None, "rows": None,
        "message": "", "progress": 0, "started_at": None,
    })
    return JSONResponse({"ok": True})
