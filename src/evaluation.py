"""
evaluation.py — Model and Clustering Evaluation

Computes evaluation metrics for the clustering models and CLV prediction models,
including Silhouette Score, Davies-Bouldin Index, and MAE/RMSE vs actual purchases
and revenue on a temporal holdout split.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from src.config import Config, load_config
from src.data_loader import clean_data, load_transaction_data
from src.feature_engineering import compute_lifetimes_rfm, compute_standard_rfm
from src.clv_model import fit_bgnd_model, fit_gg_model, predict_expected_profit, temporal_split

logger = logging.getLogger(__name__)


def evaluate_clustering(df_segmented: pd.DataFrame, features: list[str]) -> Dict[str, float]:
    """Compute clustering validation metrics.

    Args:
        df_segmented: Segmented customer DataFrame (with 'cluster' column).
        features: List of feature names used for clustering.

    Returns:
        Dict of clustering metrics.

    Example:
        >>> metrics = evaluate_clustering(df, ['recency', 'frequency', 'monetary', 'tenure'])
    """
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

    X = df_segmented[features].values
    labels = df_segmented["cluster"].values

    if len(np.unique(labels)) < 2:
        logger.warning("Fewer than 2 clusters found. Skipping clustering evaluation.")
        return {}

    # Scale for metric calculations
    X_scaled = StandardScaler().fit_transform(X)

    sil = silhouette_score(X_scaled, labels)
    db = davies_bouldin_score(X_scaled, labels)
    ch = calinski_harabasz_score(X_scaled, labels)

    logger.info(f"Clustering Eval — Silhouette: {sil:.4f}, DB Index: {db:.4f}, CH Index: {ch:.4f}")
    return {
        "silhouette_score": float(sil),
        "davies_bouldin_index": float(db),
        "calinski_harabasz_index": float(ch),
    }


def evaluate_clv_model(
    config: Config,
) -> Tuple[Dict[str, float], pd.DataFrame]:
    """Evaluate BG/NBD and Gamma-Gamma model predictions on a temporal test split.

    Args:
        config: Typed project configuration dataclass.

    Returns:
        Tuple of (metrics dictionary, customer evaluation DataFrame).

    Example:
        >>> clv_metrics, eval_df = evaluate_clv_model(cfg)
    """
    df_raw = load_transaction_data(config)
    df_clean = clean_data(df_raw)

    # Perform temporal split
    df_train, df_test = temporal_split(df_clean, train_ratio=0.8)

    # Observation end date for train is max date in train
    split_date = df_train["InvoiceDate"].max() + pd.Timedelta(seconds=1)

    # Compute lifetimes RFM on train
    rfm_train = compute_lifetimes_rfm(df_train, split_date)

    # Fit models
    bgf = fit_bgnd_model(rfm_train, config.model.bgn_penalizer)
    ggf = fit_gg_model(rfm_train, config.model.gg_penalizer)

    # Find holdout period length (in days)
    test_days = (df_test["InvoiceDate"].max() - df_test["InvoiceDate"].min()).days
    if test_days <= 0:
        test_days = config.data.prediction_days

    # Aggregate actuals on test set
    test_actuals = df_test.groupby("CustomerID").agg(
        actual_purchases=("InvoiceDate", lambda x: x.dt.date.nunique()),
        actual_revenue=("TotalPrice", "sum"),
    )

    # Join actuals to train customer list
    eval_df = rfm_train.join(test_actuals, how="left")
    eval_df["actual_purchases"] = eval_df["actual_purchases"].fillna(0)
    eval_df["actual_revenue"] = eval_df["actual_revenue"].fillna(0.0)

    # Generate predictions for the test duration
    eval_df["predicted_purchases"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        test_days,
        eval_df["frequency_lifetimes"],
        eval_df["recency_lifetimes"],
        eval_df["T_lifetimes"],
    )
    eval_df["predicted_purchases"] = eval_df["predicted_purchases"].fillna(0.0)

    returning_avg = eval_df.loc[
        eval_df["frequency_lifetimes"] > 0, "monetary_value_lifetimes"
    ].mean()
    if pd.isna(returning_avg):
        returning_avg = eval_df["monetary_value_lifetimes"].mean()

    eval_df["expected_avg_profit"] = predict_expected_profit(ggf, eval_df, returning_avg)
    eval_df["predicted_revenue"] = eval_df["predicted_purchases"] * eval_df["expected_avg_profit"]
    eval_df["predicted_revenue"] = eval_df["predicted_revenue"].fillna(0.0)

    # Compute errors
    p_mae = mean_absolute_error(eval_df["actual_purchases"], eval_df["predicted_purchases"])
    p_rmse = root_mean_squared_error(eval_df["actual_purchases"], eval_df["predicted_purchases"])
    r_mae = mean_absolute_error(eval_df["actual_revenue"], eval_df["predicted_revenue"])
    r_rmse = root_mean_squared_error(eval_df["actual_revenue"], eval_df["predicted_revenue"])

    metrics = {
        "bgnbd_log_likelihood": float(-bgf._negative_log_likelihood_),
        "gamma_gamma_log_likelihood": float(-ggf._negative_log_likelihood_),
        "test_holdout_days": int(test_days),
        "purchases_mae": float(p_mae),
        "purchases_rmse": float(p_rmse),
        "revenue_mae": float(r_mae),
        "revenue_rmse": float(r_rmse),
    }

    logger.info(
        f"CLV Evaluation — Purchases MAE: {p_mae:.4f}, Revenue MAE: {r_mae:.2f}"
    )
    return metrics, eval_df


def profile_segments(df_segmented: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Compute statistics for each customer segment.

    Args:
        df_segmented: Segmented customer DataFrame.

    Returns:
        Dictionary containing segment profiling statistics.

    Example:
        >>> profiles = profile_segments(df)
    """
    profiles = {}
    grouped = df_segmented.groupby("segment", observed=False)

    for name, group in grouped:
        profiles[str(name)] = {
            "customer_count": int(len(group)),
            "average_recency": float(group["recency"].mean()),
            "average_frequency": float(group["frequency"].mean()),
            "average_monetary": float(group["monetary"].mean()),
            "average_tenure": float(group["tenure"].mean()),
            "average_clv": float(group["clv"].mean()) if "clv" in group.columns else 0.0,
            "average_churn_probability": float(group["churn_probability"].mean())
            if "churn_probability" in group.columns
            else 0.0,
            "total_revenue": float(group["monetary"].sum() * group["frequency"].sum()),  # rough estimate
        }
    return profiles


def run_evaluation(config: Config) -> None:
    """Run the complete evaluation suite and save results to evaluation_metrics.json.

    Args:
        config: Typed project configuration dataclass.

    Example:
        >>> run_evaluation(cfg)
    """
    logger.info("Running evaluation pipeline...")

    # Evaluate CLV prediction model
    clv_metrics, _ = evaluate_clv_model(config)

    # Evaluate clustering
    segmented_path = os.path.join(config.data.processed_path, "04_customer_segments.csv")
    if os.path.exists(segmented_path):
        df_seg = pd.read_csv(segmented_path, index_col="CustomerID")
        features = ["recency", "frequency", "monetary", "tenure"]
        if "clv" in df_seg.columns:
            features.append("clv")
        clustering_metrics = evaluate_clustering(df_seg, features)
        segment_stats = profile_segments(df_seg)
    else:
        clustering_metrics = {}
        segment_stats = {}
        logger.warning(f"Segmented data not found at {segmented_path}. Skipping clustering eval.")

    # Combine all metrics
    evaluation_summary = {
        "clv_model_evaluation": clv_metrics,
        "clustering_evaluation": clustering_metrics,
        "segment_profiles": segment_stats,
    }

    os.makedirs("models", exist_ok=True)
    out_path = "models/evaluation_metrics.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(evaluation_summary, fh, indent=2)

    logger.info(f"Saved evaluation summary to {out_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    run_evaluation(cfg)
