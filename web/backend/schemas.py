"""
schemas.py — Pydantic Response Models

All API response shapes are defined here to ensure consistent,
typed JSON output from every endpoint.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    pipeline_ready: bool
    data_loaded: bool


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

class OverviewKPIs(BaseModel):
    total_customers: int
    total_revenue: float
    avg_clv: float
    avg_churn_pct: float
    num_segments: int
    prediction_days: int


class SegmentShare(BaseModel):
    segment: str
    count: int
    total_clv: float
    pct_customers: float


class OverviewResponse(BaseModel):
    kpis: OverviewKPIs
    segment_shares: List[SegmentShare]
    pipeline_last_run: Optional[str]


# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------

class SegmentProfile(BaseModel):
    name: str
    customer_count: int
    avg_recency: float
    avg_frequency: float
    avg_monetary: float
    avg_tenure: float
    avg_clv: float
    avg_churn_probability: float
    total_clv: float
    color: str


class SegmentsResponse(BaseModel):
    segments: List[SegmentProfile]
    clustering_metrics: Dict[str, float]
    algorithm: str
    optimal_k: int


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class Recommendation(BaseModel):
    segment: str
    tier: str          # "high" | "medium" | "low" | "lost" | "new"
    headline: str
    actions: List[str]
    color: str
    icon: str          # SVG path string for the frontend icon


class RecommendationsResponse(BaseModel):
    recommendations: List[Recommendation]
    generated_from: str   # e.g. "4 segments · K-Means k=4"


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

class CustomerRow(BaseModel):
    customer_id: int
    segment: str
    recency: float
    frequency: float
    monetary: float
    tenure: float
    clv: float
    churn_probability: float
    predicted_purchases: float


class CustomerDetail(BaseModel):
    customer_id: int
    segment: str
    recency: float
    frequency: float
    monetary: float
    tenure: float
    clv: float
    churn_probability: float
    predicted_purchases: float
    expected_avg_profit: float
    pca_1: float
    pca_2: float
    frequency_lifetimes: float
    recency_lifetimes: float
    T_lifetimes: float
    monetary_value_lifetimes: float


class CustomersResponse(BaseModel):
    customers: List[CustomerRow]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Models / Insights
# ---------------------------------------------------------------------------

class ModelMetrics(BaseModel):
    bgnbd_log_likelihood: float
    gamma_gamma_log_likelihood: float
    test_holdout_days: int
    purchases_mae: float
    purchases_rmse: float
    revenue_mae: float
    revenue_rmse: float


class ClusteringMetrics(BaseModel):
    silhouette_score: float
    davies_bouldin_index: float
    calinski_harabasz_index: float


class MetricsResponse(BaseModel):
    clv_model: ModelMetrics
    clustering: ClusteringMetrics


class PCAPoint(BaseModel):
    customer_id: int
    pca_1: float
    pca_2: float
    segment: str
    clv: float


class PCAResponse(BaseModel):
    points: List[PCAPoint]


class AliveMatrixResponse(BaseModel):
    frequency_range: List[int]
    recency_range: List[int]
    matrix: List[List[float]]


class CLVBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class CLVDistributionResponse(BaseModel):
    bins: List[CLVBin]
    mean: float
    median: float
    p90: float


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class PipelineRunResponse(BaseModel):
    success: bool
    message: str
    duration_seconds: Optional[float]


class PipelineStatusResponse(BaseModel):
    last_run: Optional[str]
    algorithm: str
    optimal_k: int
    metrics: Dict[str, float]
    segment_counts: Dict[str, int]
