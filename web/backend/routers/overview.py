"""
overview.py — Overview API Router

Provides KPI summary and segment share data for the Overview page.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from web.backend.schemas import OverviewKPIs, OverviewResponse, SegmentShare
from web.backend.services.data_service import get_data_service

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.config import load_config

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
def get_overview() -> OverviewResponse:
    """Return top-level KPIs and segment distribution for the overview page."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded. Run the ML pipeline first.")

    df = svc.df_segments
    cfg = load_config()

    total_customers = len(df)
    total_revenue = svc.get_total_revenue()
    avg_clv = float(df["clv"].mean()) if "clv" in df.columns else 0.0
    avg_churn = float(df["churn_probability"].mean()) if "churn_probability" in df.columns else 0.0
    num_segments = int(df["segment"].nunique())

    kpis = OverviewKPIs(
        total_customers=total_customers,
        total_revenue=round(total_revenue, 2),
        avg_clv=round(avg_clv, 2),
        avg_churn_pct=round(avg_churn * 100, 2),
        num_segments=num_segments,
        prediction_days=cfg.data.prediction_days,
    )

    # Segment shares
    shares = []
    for seg_name, group in df.groupby("segment", observed=False):
        count = len(group)
        total_clv = float(group["clv"].sum()) if "clv" in group.columns else 0.0
        shares.append(
            SegmentShare(
                segment=str(seg_name),
                count=count,
                total_clv=round(total_clv, 2),
                pct_customers=round(count / total_customers * 100, 1),
            )
        )

    # Sort by count descending
    shares.sort(key=lambda x: x.count, reverse=True)

    # Last pipeline run
    last_run = None
    if svc.runs_data:
        last_run = svc.runs_data.get("last_run")

    return OverviewResponse(kpis=kpis, segment_shares=shares, pipeline_last_run=last_run)
