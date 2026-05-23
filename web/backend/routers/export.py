"""
export.py — Export API Router

Provides CSV download and PDF report generation endpoints.
"""

from __future__ import annotations

import io
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from web.backend.services.data_service import get_data_service
from web.backend.services.report_service import generate_pdf_report

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv")
def download_csv() -> StreamingResponse:
    """Stream the customer segments CSV as a download."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    csv_bytes = svc.df_segments.to_csv(index=True).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clv_customer_segments.csv"},
    )


@router.get("/pdf")
def download_pdf() -> FileResponse:
    """Generate and return the PDF executive summary report."""
    output_path = "reports/output/clv_segmentation_report.pdf"
    success, result = generate_pdf_report(output_path=output_path)

    if not success:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {result}")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="PDF file not found after generation.")

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="clv_segmentation_report.pdf",
    )
