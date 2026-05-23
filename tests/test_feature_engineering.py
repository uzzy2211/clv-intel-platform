"""
test_features.py — Unit Tests for RFM Feature Engineering

Verifies standard and lifetimes RFM feature calculations on synthetic data.
"""

from __future__ import annotations

import pandas as pd
import pytest
from src.feature_engineering import compute_standard_rfm, compute_lifetimes_rfm


@pytest.fixture
def mock_transaction_data() -> pd.DataFrame:
    """Fixture providing a mock cleaned transaction dataset.

    Contains 2 customers:
    - Customer 1:
      - 2024-01-01: TotalPrice = 100.0 (Invoice 500001)
      - 2024-01-05: TotalPrice = 150.0 (Invoice 500002)
    - Customer 2:
      - 2024-01-02: TotalPrice = 50.0  (Invoice 500003)
    """
    return pd.DataFrame(
        {
            "CustomerID": [1.0, 1.0, 2.0],
            "InvoiceNo": ["500001", "500002", "500003"],
            "InvoiceDate": pd.to_datetime(
                ["2024-01-01 10:00:00", "2024-01-05 12:00:00", "2024-01-02 09:30:00"]
            ),
            "TotalPrice": [100.0, 150.0, 50.0],
        }
    )


def test_compute_standard_rfm(mock_transaction_data: pd.DataFrame):
    """Test standard RFM computation for Recency, Frequency, Monetary, and Tenure."""
    # Use Jan 6 as snapshot date
    snapshot_date = pd.to_datetime("2024-01-06 00:00:00")

    rfm = compute_standard_rfm(mock_transaction_data, snapshot_date)

    # Check Customer 1
    # Recency: 2024-01-06 - 2024-01-05 = 0 days (snapshot_date.date - last_purchase.date)
    # Wait, 2024-01-06 00:00:00 - 2024-01-05 12:00:00 = 11.5 hours -> 0 days (since dt.days is used)
    # Tenure: 2024-01-06 00:00:00 - 2024-01-01 10:00:00 = 4 days 14 hours -> 4 days
    # Frequency: 2 unique dates
    # Monetary: (100.0 + 150.0) / 2 = 125.0
    assert rfm.loc[1.0, "recency"] == 0
    assert rfm.loc[1.0, "tenure"] == 4
    assert rfm.loc[1.0, "frequency"] == 2
    assert rfm.loc[1.0, "monetary"] == 125.0

    # Check Customer 2
    # Recency: 2024-01-06 00:00:00 - 2024-01-02 09:30:00 = 3 days 14.5 hours -> 3 days
    # Tenure: 2024-01-06 00:00:00 - 2024-01-02 09:30:00 = 3 days
    # Frequency: 1 unique date
    # Monetary: 50.0
    assert rfm.loc[2.0, "recency"] == 3
    assert rfm.loc[2.0, "tenure"] == 3
    assert rfm.loc[2.0, "frequency"] == 1
    assert rfm.loc[2.0, "monetary"] == 50.0


def test_compute_lifetimes_rfm(mock_transaction_data: pd.DataFrame):
    """Test lifetimes-specific RFM computation using the package utility."""
    # Use Jan 6 as snapshot date
    snapshot_date = pd.to_datetime("2024-01-06 00:00:00")

    lt_rfm = compute_lifetimes_rfm(mock_transaction_data, snapshot_date)

    # Check Customer 1
    # frequency_lifetimes: 1.0 (repeat purchase)
    # recency_lifetimes: 2024-01-05 - 2024-01-01 = 4.0
    # T_lifetimes: 2024-01-06 - 2024-01-01 = 5.0 (since observation_period_end is Jan 6)
    # monetary_value_lifetimes: 150.0 (value of the repeat purchase)
    assert lt_rfm.loc[1.0, "frequency_lifetimes"] == 1.0
    assert lt_rfm.loc[1.0, "recency_lifetimes"] == 4.0
    assert lt_rfm.loc[1.0, "T_lifetimes"] == 5.0
    assert lt_rfm.loc[1.0, "monetary_value_lifetimes"] == 150.0

    # Check Customer 2
    # frequency_lifetimes: 0.0 (no repeat purchase)
    # recency_lifetimes: 0.0
    # T_lifetimes: 2024-01-06 - 2024-01-02 = 4.0
    # monetary_value_lifetimes: 0.0
    assert lt_rfm.loc[2.0, "frequency_lifetimes"] == 0.0
    assert lt_rfm.loc[2.0, "recency_lifetimes"] == 0.0
    assert lt_rfm.loc[2.0, "T_lifetimes"] == 4.0
    assert lt_rfm.loc[2.0, "monetary_value_lifetimes"] == 0.0
