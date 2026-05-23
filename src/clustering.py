"""
clustering.py — Customer Segmentation Pipeline

Loads RFM and CLV predictions, scales them, programmatically determines the optimal
number of clusters, fits K-Means or GMM models, applies PCA for 2D visualization,
assigns human-readable segment labels based on centroid profiling, and saves the outputs.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

from src.config import Config, load_config

logger = logging.getLogger(__name__)


def scale_features(df: pd.DataFrame, features: List[str]) -> Tuple[np.ndarray, StandardScaler]:
    """Standardize the specified features in the DataFrame.

    Args:
        df: Input DataFrame.
        features: List of column names to scale.

    Returns:
        A tuple of (scaled feature array, fitted StandardScaler).

    Example:
        >>> X_scaled, scaler = scale_features(rfm_df, ['recency', 'frequency'])
    """
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[features])
    return X_scaled, scaler


def find_optimal_k(
    X_scaled: np.ndarray, k_min: int, k_max: int, random_state: int
) -> Tuple[int, Dict[int, float]]:
    """Determine the optimal number of clusters using Silhouette Score.

    Args:
        X_scaled: Scaled feature array.
        k_min: Minimum number of clusters to evaluate.
        k_max: Maximum number of clusters to evaluate.
        random_state: Random seed for reproducibility.

    Returns:
        A tuple of (optimal k, dict mapping k to silhouette score).

    Example:
        >>> opt_k, scores = find_optimal_k(X_scaled, 2, 8, 42)
    """
    n_samples = X_scaled.shape[0]

    # Cap k_max so we never request more clusters than samples
    safe_k_max = min(k_max, n_samples - 1)
    safe_k_min = min(k_min, safe_k_max)

    if safe_k_max < 2:
        logger.warning(
            f"Only {n_samples} samples — cannot compute silhouette. Defaulting to k=2."
        )
        return 2, {2: 0.0}

    if safe_k_max != k_max:
        logger.warning(
            f"k_max capped from {k_max} to {safe_k_max} (only {n_samples} samples)."
        )

    scores: Dict[int, float] = {}
    optimal_k = safe_k_min
    best_score = -1.0

    for k in range(safe_k_min, safe_k_max + 1):
        try:
            kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
            labels = kmeans.fit_predict(X_scaled)
            score = silhouette_score(X_scaled, labels)
            scores[k] = float(score)
            logger.info(f"Evaluated k={k}: Silhouette Score = {score:.4f}")
            if score > best_score:
                best_score = score
                optimal_k = k
        except Exception as exc:
            logger.warning(f"k={k} evaluation failed: {exc}")
            scores[k] = -1.0

    logger.info(f"Optimal k = {optimal_k} (score {best_score:.4f})")
    return optimal_k, scores


def label_segments(df: pd.DataFrame, centroids: np.ndarray, features: List[str]) -> pd.Series:
    """Assign human-readable segment names to clusters based on centroid values.

    Calculates a combined value score for each cluster centroid:
    score = frequency + monetary - recency + tenure + clv (if present)
    and maps them to appropriate segments.

    Args:
        df: DataFrame containing the 'cluster' column.
        centroids: Array of cluster centroids from the fitted model.
        features: List of features used to fit the model.

    Returns:
        Series containing categorical segment labels.

    Example:
        >>> df['segment'] = label_segments(df, kmeans.cluster_centers_, features)
    """
    # Scale centroids to standardize feature scales for ranking
    scaler = StandardScaler()
    scaled_centroids = scaler.fit_transform(centroids)

    # Feature indices
    r_idx = features.index("recency")
    f_idx = features.index("frequency")
    m_idx = features.index("monetary")
    t_idx = features.index("tenure")
    clv_idx = features.index("clv") if "clv" in features else -1

    # Calculate ranking score: high frequency, high monetary, high tenure, low recency, high clv
    value_scores = (
        scaled_centroids[:, f_idx]
        + scaled_centroids[:, m_idx]
        + scaled_centroids[:, t_idx]
        - scaled_centroids[:, r_idx]
    )
    if clv_idx != -1:
        value_scores += scaled_centroids[:, clv_idx]

    # Sort cluster indices by value score descending
    sorted_clusters = np.argsort(value_scores)[::-1]
    k = len(centroids)

    # Map rank to segment name
    cluster_to_segment = {}
    if k == 2:
        cluster_to_segment[sorted_clusters[0]] = "High Value Customers"
        cluster_to_segment[sorted_clusters[1]] = "Low Value / Lost"
    elif k == 3:
        cluster_to_segment[sorted_clusters[0]] = "Champions"
        cluster_to_segment[sorted_clusters[1]] = "Loyal Customers"
        cluster_to_segment[sorted_clusters[2]] = "Hibernating"
    elif k == 4:
        cluster_to_segment[sorted_clusters[0]] = "Champions"
        cluster_to_segment[sorted_clusters[1]] = "Loyal Customers"
        cluster_to_segment[sorted_clusters[2]] = "At Risk"
        cluster_to_segment[sorted_clusters[3]] = "Lost"
    else:
        # 5 or more clusters
        cluster_to_segment[sorted_clusters[0]] = "Champions"
        cluster_to_segment[sorted_clusters[1]] = "Loyal Customers"
        remaining = list(sorted_clusters[2:])
        highest_recency_idx = np.argmax(scaled_centroids[remaining, r_idx])
        at_risk_cluster = remaining.pop(highest_recency_idx)
        cluster_to_segment[at_risk_cluster] = "At Risk"

        if remaining:
            lowest_tenure_idx = np.argmin(scaled_centroids[remaining, t_idx])
            new_cust_cluster = remaining.pop(lowest_tenure_idx)
            cluster_to_segment[new_cust_cluster] = "New Customers"

        for idx in remaining:
            cluster_to_segment[idx] = "Hibernating"

    segment_series = df["cluster"].map(cluster_to_segment)
    return pd.Categorical(segment_series)


def train_clustering(config: Config) -> pd.DataFrame:
    """Load CLV predictions, fit K-Means or GMM model, assign segments, and save.

    Args:
        config: Typed project configuration dataclass.

    Returns:
        DataFrame containing RFM features, CLV, and assigned segments.

    Example:
        >>> segmented_df = train_clustering(config)
    """
    input_path = os.path.join(config.data.processed_path, "03_clv_predictions.csv")
    fallback_path = os.path.join(config.data.processed_path, "02_rfm_features.csv")

    # Fallback to RFM features if CLV predictions are not yet generated
    if os.path.exists(input_path):
        df = pd.read_csv(input_path, index_col="CustomerID")
        features = ["recency", "frequency", "monetary", "tenure", "clv"]
    elif os.path.exists(fallback_path):
        logger.warning("CLV predictions file not found. Falling back to RFM features.")
        df = pd.read_csv(fallback_path, index_col="CustomerID")
        features = ["recency", "frequency", "monetary", "tenure"]
    else:
        raise FileNotFoundError(
            f"No features file found at '{input_path}' or '{fallback_path}'."
        )

    logger.info(f"Loaded {len(df)} customer profiles for clustering.")

    # Scale features
    X_scaled, scaler = scale_features(df, features)

    # Determine optimal k using K-Means silhouette scores
    k_range = config.model.clustering.k_range
    random_state = config.model.clustering.random_state
    optimal_k, sil_scores = find_optimal_k(X_scaled, k_range[0], k_range[1], random_state)

    # Fit final clustering model
    algo = config.model.clustering.algorithm.lower()
    logger.info(f"Fitting final {algo.upper()} model with k={optimal_k}")

    if algo == "kmeans":
        model = KMeans(n_clusters=optimal_k, random_state=random_state, n_init=10)
        df["cluster"] = model.fit_predict(X_scaled)
        centroids = model.cluster_centers_
    elif algo == "gmm":
        model = GaussianMixture(n_components=optimal_k, random_state=random_state, n_init=10)
        df["cluster"] = model.fit_predict(X_scaled)
        centroids = model.means_
    else:
        raise ValueError(f"Unsupported algorithm '{algo}' in config.")

    # Assign segment labels
    df["segment"] = label_segments(df, centroids, features)

    # Apply 2D PCA for scatter visualization
    pca = PCA(n_components=2, random_state=random_state)
    X_pca = pca.fit_transform(X_scaled)
    df["pca_1"] = X_pca[:, 0]
    df["pca_2"] = X_pca[:, 1]

    # Compute evaluation metrics
    db_index = davies_bouldin_score(X_scaled, df["cluster"])
    ch_index = calinski_harabasz_score(X_scaled, df["cluster"])
    final_sil = sil_scores[optimal_k]

    logger.info(
        f"Clustering Metrics: Silhouette={final_sil:.4f}, "
        f"Davies-Bouldin={db_index:.4f}, Calinski-Harabasz={ch_index:.4f}"
    )

    # Save output dataset
    output_path = os.path.join(config.data.processed_path, "04_customer_segments.csv")
    df.to_csv(output_path, index=True)
    logger.info(f"Saved segmented customer data to {output_path}")

    # Serialize model artifacts
    os.makedirs("models", exist_ok=True)
    joblib.dump(scaler, "models/scaler.joblib")
    joblib.dump(model, f"models/{algo}_model.joblib")
    joblib.dump(pca, "models/pca_model.joblib")
    logger.info("Saved scaler, model, and PCA artifacts to models/ directory.")

    # Log run summary
    run_summary = {
        "algorithm": algo,
        "optimal_k": optimal_k,
        "parameters": {
            "random_state": random_state,
            "k_range": k_range,
        },
        "metrics": {
            "silhouette_score": final_sil,
            "davies_bouldin_index": db_index,
            "calinski_harabasz_index": ch_index,
        },
        "segment_counts": df["segment"].value_counts().to_dict(),
    }
    with open("models/runs.json", "w", encoding="utf-8") as fh:
        json.dump(run_summary, fh, indent=2)

    logger.info("Saved run details and metrics to models/runs.json")
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    train_clustering(cfg)
