"""
test_data_loader.py — Unit Tests for Data Ingestion & Cleaning

Verifies schema validation, data cleaning, and observation window filtering.
"""

from __future__ import annotations

import pandas as pd
import pytest
from src.config import Config, DataConfig, ModelConfig, ClusteringConfig, DashboardConfig, ReportConfig
from src.data_loader import validate_schema, clean_data, filter_by_observation_window


@pytest.fixture
def sample_transaction_df() -> pd.DataFrame:
    """Fixture providing a standard valid transaction DataFrame."""
    return pd.DataFrame(
        {
            "InvoiceNo": ["500001", "500002", "C500003", "500004", "500005"],
            "StockCode": ["85123A", "71053", "84406B", "84029G", "22752"],
            "Description": ["Product A", "Product B", "Product C", "Product D", "Product E"],
            "Quantity": [6, 2, -1, 10, 0],
            "InvoiceDate": [
                "2024-01-01 10:00:00",
                "2024-06-01 12:00:00",
                "2024-06-15 14:00:00",
                "2024-12-01 09:30:00",
                "2024-12-02 11:00:00",
            ],
            "UnitPrice": [2.54, 1.0, 5.0, 10.5, 2.0],
            "CustomerID": [12345.0, 12346.0, 12345.0, None, 12347.0],
            "Country": ["United Kingdom", "France", "United Kingdom", "United Kingdom", "Germany"],
        }
    )


@pytest.fixture
def mock_config() -> Config:
    """Fixture providing a mock Config object."""
    data_cfg = DataConfig(
        raw_path="data/raw/online_retail_II.csv",
        synthetic_path="data/synthetic/synthetic_data.csv",
        processed_path="data/processed/",
        snapshot_date=None,
        observation_months=6,
        prediction_days=90,
    )
    clustering_cfg = ClusteringConfig(k_range=[2, 5], algorithm="kmeans", random_state=42)
    model_cfg = ModelConfig(bgn_penalizer=0.001, gg_penalizer=0.001, clustering=clustering_cfg)
    dashboard_cfg = DashboardConfig(port=8501, theme="light")
    report_cfg = ReportConfig(output_dir="reports/output/", margin_rate=0.10, discount_rate=0.01)

    return Config(
        data=data_cfg,
        model=model_cfg,
        dashboard=dashboard_cfg,
        report=report_cfg,
    )


def test_validate_schema_success(sample_transaction_df: pd.DataFrame):
    """Test that a valid DataFrame passes schema validation without raising errors."""
    try:
        validate_schema(sample_transaction_df)
    except (ValueError, TypeError) as exc:
        pytest.fail(f"validate_schema failed on valid DataFrame with error: {exc}")


def test_validate_schema_missing_columns(sample_transaction_df: pd.DataFrame):
    """Test that missing required columns raise a ValueError."""
    invalid_df = sample_transaction_df.drop(columns=["InvoiceNo", "CustomerID"])
    with pytest.raises(ValueError, match="Required columns missing"):
        validate_schema(invalid_df)


def test_validate_schema_invalid_types(sample_transaction_df: pd.DataFrame):
    """Test that non-numeric Quantity or UnitPrice columns raise a TypeError."""
    invalid_qty_df = sample_transaction_df.copy()
    invalid_qty_df["Quantity"] = ["six", "two", "minus-one", "ten", "zero"]
    with pytest.raises(TypeError, match="Quantity.*must contain numeric"):
        validate_schema(invalid_qty_df)

    invalid_price_df = sample_transaction_df.copy()
    invalid_price_df["UnitPrice"] = ["2.54", "1.0", "5.0", "10.5", "2.0"]
    with pytest.raises(TypeError, match="UnitPrice.*must contain numeric"):
        validate_schema(invalid_price_df)


def test_clean_data(sample_transaction_df: pd.DataFrame):
    """Test data cleaning logic: nulls, cancellations, positive checks, and total price."""
    cleaned = clean_data(sample_transaction_df)

    # 1. Null customer ID should be removed (Invoice 500004 had None CustomerID)
    assert not cleaned["CustomerID"].isna().any()

    # 2. Cancelled invoices should be removed (Invoice C500003)
    assert not cleaned["InvoiceNo"].str.startswith("C").any()

    # 3. Quantity and UnitPrice must be > 0 (Invoice 500005 has Quantity = 0)
    assert (cleaned["Quantity"] > 0).all()
    assert (cleaned["UnitPrice"] > 0).all()

    # 4. TotalPrice should be correctly calculated
    expected_total_price = cleaned["Quantity"] * cleaned["UnitPrice"]
    pd.testing.assert_series_equal(cleaned["TotalPrice"], expected_total_price, check_names=False)

    # 5. Check remaining records (Only invoices 500001 and 500002 should survive)
    assert len(cleaned) == 2
    assert set(cleaned["InvoiceNo"]) == {"500001", "500002"}


def test_filter_by_observation_window_auto(sample_transaction_df: pd.DataFrame, mock_config: Config):
    """Test observation window filtering using auto-calculated snapshot date."""
    # Clean first so dates are parsed and columns are correct
    cleaned = clean_data(sample_transaction_df)

    # max date in cleaned is '2024-06-01 12:00:00' (from 500002)
    # snapshot date = max date + 1 day = 2024-06-02 12:00:00
    # observation window start = 6 months prior = 2023-12-02 12:00:00
    # Invoice 500001 (2024-01-01) and 500002 (2024-06-01) should fall in window
    filtered = filter_by_observation_window(cleaned, mock_config)
    assert len(filtered) == 2


def test_filter_by_observation_window_explicit(sample_transaction_df: pd.DataFrame, mock_config: Config):
    """Test observation window filtering using an explicit snapshot date."""
    cleaned = clean_data(sample_transaction_df)

    # Set explicit snapshot date to 2024-04-01
    # observation window start = 6 months prior = 2023-10-01
    # Only 500001 (2024-01-01) falls within [2023-10-01, 2024-04-01)
    mock_config.data.snapshot_date = "2024-04-01 00:00:00"
    filtered = filter_by_observation_window(cleaned, mock_config)
    assert len(filtered) == 1
    assert filtered.iloc[0]["InvoiceNo"] == "500001"
