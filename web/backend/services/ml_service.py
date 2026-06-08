"""
ml_service.py — ML Pipeline Service

Wraps the existing src/ ML pipeline to allow triggering a full
re-run from the API, and provides model-specific computations
like the BG/NBD alive probability matrix.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Path setup is handled by the application entry points (main.py, run.py, or pytest)


logger = logging.getLogger(__name__)


def run_full_pipeline() -> Tuple[bool, str, float]:
    """Execute the full ML pipeline: features → CLV → clustering → evaluation.

    Returns:
        Tuple of (success, message, duration_seconds).
    """
    start = time.time()
    try:
        from src.config import load_config
        from src.feature_engineering import engineer_features
        from src.clv_model import run_clv_pipeline
        from src.clustering import train_clustering
        from src.evaluation import run_evaluation

        cfg = load_config()
        logger.info("Pipeline: engineering features...")
        engineer_features(cfg)

        logger.info("Pipeline: running CLV model...")
        run_clv_pipeline(cfg)

        logger.info("Pipeline: clustering customers...")
        train_clustering(cfg)

        logger.info("Pipeline: evaluating models...")
        run_evaluation(cfg)

        duration = time.time() - start
        logger.info(f"Pipeline completed in {duration:.1f}s")
        return True, "Pipeline completed successfully.", duration

    except Exception as exc:
        duration = time.time() - start
        logger.error(f"Pipeline failed: {exc}", exc_info=True)
        return False, str(exc), duration


def compute_alive_matrix(
    bgf_model_path: str = "models/bgf_model.pkl",
    max_frequency: int = 30,
    max_recency: int = 365,
    recency_step: int = 7,
    max_t: int = 365,
) -> Dict[str, Any]:
    """Compute the BG/NBD probability-alive matrix for the heatmap.

    Args:
        bgf_model_path: Path to the serialized BG/NBD model.
        max_frequency: Maximum frequency axis value.
        max_recency: Maximum recency axis value (days).
        recency_step: Step size for recency axis.
        max_t: Customer age (T) to use for the matrix.

    Returns:
        Dict with frequency_range, recency_range, and matrix values.
    """
    try:
        from lifetimes import BetaGeoFitter
        bgf = BetaGeoFitter()
        bgf.load_model(bgf_model_path)

        freq_range = list(range(0, max_frequency + 1, 1))
        rec_range = list(range(0, max_recency + 1, recency_step))

        ff, rr = np.meshgrid(freq_range, rec_range)
        matrix = bgf.conditional_probability_alive(ff, rr, max_t)

        # Replace NaN with 0
        matrix = np.nan_to_num(matrix, nan=0.0)

        return {
            "frequency_range": freq_range,
            "recency_range": rec_range,
            "matrix": matrix.tolist(),
        }
    except Exception as exc:
        logger.error(f"Failed to compute alive matrix: {exc}")
        return {"frequency_range": [], "recency_range": [], "matrix": []}


def compute_clv_distribution(df_segments, n_bins: int = 40) -> List[Dict[str, Any]]:
    """Compute histogram bins for the CLV distribution.

    Args:
        df_segments: Customer segments DataFrame with 'clv' column.
        n_bins: Number of histogram bins.

    Returns:
        List of bin dicts with bin_start, bin_end, count.
    """
    if df_segments is None or "clv" not in df_segments.columns:
        return []

    clv_vals = df_segments["clv"].dropna().values
    counts, edges = np.histogram(clv_vals, bins=n_bins)

    return [
        {
            "bin_start": float(edges[i]),
            "bin_end": float(edges[i + 1]),
            "count": int(counts[i]),
        }
        for i in range(len(counts))
    ]

def compute_churn_risk(df_transactions) -> pd.DataFrame:
    """Compute churn risk flags for customers.

    A customer is flagged as 'High Risk' if:
    - Days since last purchase > 90 days, OR
    - Purchase frequency is <= 50% of the overall average frequency.

    The function expects a DataFrame with at least:
    - 'customer_id' (or similar identifier)
    - 'date' column (datetime) indicating each transaction date.

    Returns the original DataFrame with an added column 'churn_risk' containing
    either 'High Risk' or 'Low Risk'.
    """
    import pandas as pd
    from datetime import datetime

    if df_transactions is None or df_transactions.empty:
        return pd.DataFrame()

    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_transactions['date']):
        df_transactions = df_transactions.copy()
        df_transactions['date'] = pd.to_datetime(df_transactions['date'], errors='coerce')

    # Days since last purchase per customer
    last_purchase = df_transactions.groupby('customer_id')['date'].max().reset_index()
    last_purchase['days_since'] = (datetime.utcnow() - last_purchase['date']).dt.days

    # Purchase frequency per customer (total transactions)
    freq = df_transactions.groupby('customer_id').size().reset_index(name='freq')
    avg_freq = freq['freq'].mean()

    # Merge flags
    flags = pd.merge(last_purchase, freq, on='customer_id')
    flags['churn_risk'] = flags.apply(
        lambda row: 'High Risk' if (row['days_since'] > 90 or row['freq'] <= 0.5 * avg_freq) else 'Low Risk',
        axis=1,
    )

    # Merge back to original dataframe (one row per customer)
    result = pd.merge(df_transactions, flags[['customer_id', 'churn_risk']].drop_duplicates(), on='customer_id', how='left')
    return result

