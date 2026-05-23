"""
test_clustering.py — Unit Tests for Customer Segmentation Pipeline

Verifies scaling, optimal k search, and segment labeling heuristics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.clustering import scale_features, find_optimal_k, label_segments


@pytest.fixture
def mock_rfm_data() -> pd.DataFrame:
    """Fixture providing a mock RFM dataset for testing clustering helper functions."""
    return pd.DataFrame(
        {
            "recency": [10, 100, 5, 120, 80],
            "frequency": [20, 2, 18, 1, 3],
            "monetary": [500.0, 30.0, 450.0, 20.0, 45.0],
            "tenure": [300, 150, 320, 120, 180],
        },
        index=[1.0, 2.0, 3.0, 4.0, 5.0],
    )


def test_scale_features(mock_rfm_data: pd.DataFrame):
    """Test feature scaling returns correct shapes and is standardized."""
    features = ["recency", "frequency", "monetary", "tenure"]
    X_scaled, scaler = scale_features(mock_rfm_data, features)

    assert X_scaled.shape == (5, 4)
    # Means should be very close to 0 after standard scaling
    assert np.allclose(X_scaled.mean(axis=0), 0.0, atol=1e-7)
    # Stds should be very close to 1
    assert np.allclose(X_scaled.std(axis=0), 1.0, atol=1e-7)


def test_find_optimal_k():
    """Test optimal cluster number identification on a simple structured array."""
    # Create two very distinct clusters
    np.random.seed(42)
    c1 = np.random.normal(loc=0.0, scale=0.1, size=(10, 4))
    c2 = np.random.normal(loc=10.0, scale=0.1, size=(10, 4))
    X_scaled = np.vstack([c1, c2])

    opt_k, scores = find_optimal_k(X_scaled, k_min=2, k_max=4, random_state=42)

    # 2 is clearly the optimal number of clusters for this data
    assert opt_k == 2
    assert 2 in scores
    assert 3 in scores
    assert scores[2] > scores[3]


def test_label_segments_2_clusters():
    """Test human-readable segment labeling for k=2 clusters."""
    df = pd.DataFrame({"cluster": [0, 1, 0, 1, 0]})
    # Centroid 0: Low recency, High frequency, High monetary, High tenure (High Value)
    # Centroid 1: High recency, Low frequency, Low monetary, Low tenure (Low Value)
    centroids = np.array(
        [[5.0, 20.0, 500.0, 300.0], [100.0, 2.0, 30.0, 100.0]]  # Centroid 0  # Centroid 1
    )
    features = ["recency", "frequency", "monetary", "tenure"]

    segments = label_segments(df, centroids, features)

    assert segments[0] == "High Value Customers"
    assert segments[1] == "Low Value / Lost"
    assert set(segments.categories) == {"High Value Customers", "Low Value / Lost"}
