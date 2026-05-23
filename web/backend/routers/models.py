"""
models.py — Model Insights API Router

Provides evaluation metrics, PCA scatter data, alive probability matrix,
and CLV distribution for the Model Insights page.
"""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException
from schemas import (
    AliveMatrixResponse,
    CLVBin,
    CLVDistributionResponse,
    ClusteringMetrics,
    MetricsResponse,
    ModelMetrics,
    PCAPoint,
    PCAResponse,
)
from services.data_service import get_data_service
from services.ml_service import compute_alive_matrix, compute_clv_distribution


def _get_matrix_cache() -> dict:
    """Lazy import to avoid circular dependency with main.py."""
    try:
        from main import get_alive_matrix_cache
        return get_alive_matrix_cache()
    except Exception:
        return {}

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    """Return CLV model and clustering evaluation metrics."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    m = svc.evaluation_metrics
    clv_m = m.get("clv_model_evaluation", {})
    cl_m = m.get("clustering_evaluation", {})

    return MetricsResponse(
        clv_model=ModelMetrics(
            bgnbd_log_likelihood=clv_m.get("bgnbd_log_likelihood", 0.0),
            gamma_gamma_log_likelihood=clv_m.get("gamma_gamma_log_likelihood", 0.0),
            test_holdout_days=clv_m.get("test_holdout_days", 0),
            purchases_mae=clv_m.get("purchases_mae", 0.0),
            purchases_rmse=clv_m.get("purchases_rmse", 0.0),
            revenue_mae=clv_m.get("revenue_mae", 0.0),
            revenue_rmse=clv_m.get("revenue_rmse", 0.0),
        ),
        clustering=ClusteringMetrics(
            silhouette_score=cl_m.get("silhouette_score", 0.0),
            davies_bouldin_index=cl_m.get("davies_bouldin_index", 0.0),
            calinski_harabasz_index=cl_m.get("calinski_harabasz_index", 0.0),
        ),
    )


@router.get("/pca", response_model=PCAResponse)
def get_pca() -> PCAResponse:
    """Return PCA scatter plot data for all customers."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    df = svc.df_segments
    if "pca_1" not in df.columns or "pca_2" not in df.columns:
        raise HTTPException(status_code=404, detail="PCA data not available.")

    points = []
    for cid, row in df.iterrows():
        points.append(
            PCAPoint(
                customer_id=int(cid),
                pca_1=round(float(row["pca_1"]), 4),
                pca_2=round(float(row["pca_2"]), 4),
                segment=str(row.get("segment", "")),
                clv=round(float(row.get("clv", 0)), 2),
            )
        )

    return PCAResponse(points=points)


@router.get("/alive-matrix", response_model=AliveMatrixResponse)
def get_alive_matrix() -> AliveMatrixResponse:
    """Return the BG/NBD probability-alive heatmap matrix (served from startup cache)."""
    result = _get_matrix_cache()
    if not result or not result.get("matrix"):
        # Fallback: compute on demand (slower)
        result = compute_alive_matrix()
    return AliveMatrixResponse(
        frequency_range=result.get("frequency_range", []),
        recency_range=result.get("recency_range", []),
        matrix=result.get("matrix", []),
    )


@router.get("/clv-distribution", response_model=CLVDistributionResponse)
def get_clv_distribution() -> CLVDistributionResponse:
    """Return histogram bins for the CLV distribution."""
    svc = get_data_service()
    if not svc.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded.")

    df = svc.df_segments
    bins_raw = compute_clv_distribution(df)
    bins = [CLVBin(**b) for b in bins_raw]

    clv_vals = df["clv"].dropna()
    return CLVDistributionResponse(
        bins=bins,
        mean=round(float(clv_vals.mean()), 2),
        median=round(float(clv_vals.median()), 2),
        p90=round(float(np.percentile(clv_vals, 90)), 2),
    )
