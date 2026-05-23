"""
features.py — RFM Feature Engineering

Aggregates raw transaction data into RFM (Recency, Frequency, Monetary,
and Tenure) summaries, including both standard metrics for clustering
and lifetimes-specific metrics for CLV prediction.
"""

from __future__ import annotations

import logging
import os
import pandas as pd
from lifetimes.utils import summary_data_from_transaction_data
from src.config import Config, load_config
from src.data_loader import clean_data, filter_by_observation_window, load_transaction_data

logger = logging.getLogger(__name__)


def compute_standard_rfm(df: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    """Compute standard RFM (Recency, Frequency, Monetary, Tenure) metrics per customer.

    Args:
        df: Cleaned and filtered transaction DataFrame.
        snapshot_date: Date reference for Recency and Tenure calculations.

    Returns:
        DataFrame with CustomerID as index and columns:
        ['recency', 'frequency', 'monetary', 'tenure']

    Example:
        >>> rfm = compute_standard_rfm(df_filtered, snapshot_date)
    """
    df_copy = df.copy()
    # Normalize datetime to date for unique purchase dates
    df_copy["InvoiceDateDate"] = df_copy["InvoiceDate"].dt.date

    # Aggregate invoice levels for monetary calculations
    invoice_totals = (
        df_copy.groupby(["CustomerID", "InvoiceNo"])["TotalPrice"]
        .sum()
        .reset_index()
    )
    monetary = invoice_totals.groupby("CustomerID")["TotalPrice"].mean()

    # Aggregate general metrics
    agg_df = df_copy.groupby("CustomerID").agg(
        first_purchase=("InvoiceDate", "min"),
        last_purchase=("InvoiceDate", "max"),
        frequency=("InvoiceDateDate", "nunique"),
    )

    agg_df["recency"] = (snapshot_date - agg_df["last_purchase"]).dt.days
    agg_df["tenure"] = (snapshot_date - agg_df["first_purchase"]).dt.days
    agg_df["monetary"] = monetary

    return agg_df[["recency", "frequency", "monetary", "tenure"]]


def compute_lifetimes_rfm(df: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    """Compute lifetimes-specific RFM metrics using lifetimes utility.

    Args:
        df: Cleaned and filtered transaction DataFrame.
        snapshot_date: Reference end date for the observation period.

    Returns:
        DataFrame with CustomerID as index and lifetimes RFM columns.

    Example:
        >>> lt_rfm = compute_lifetimes_rfm(df_filtered, snapshot_date)
    """
    # Lifetimes utility summary_data_from_transaction_data
    lt_summary = summary_data_from_transaction_data(
        df,
        customer_id_col="CustomerID",
        datetime_col="InvoiceDate",
        monetary_value_col="TotalPrice",
        observation_period_end=snapshot_date,
    )

    # Rename to prevent collision with standard RFM
    return lt_summary.rename(
        columns={
            "frequency": "frequency_lifetimes",
            "recency": "recency_lifetimes",
            "T": "T_lifetimes",
            "monetary_value": "monetary_value_lifetimes",
        }
    )


def engineer_features(config: Config) -> pd.DataFrame:
    """Load transaction data, clean it, compute all RFM metrics, and save.

    Args:
        config: Typed project configuration dataclass.

    Returns:
        Aggregated RFM DataFrame.

    Example:
        >>> rfm_df = engineer_features(config)
    """
    df = load_transaction_data(config)
    df_clean = clean_data(df)
    df_filtered = filter_by_observation_window(df_clean, config)

    if config.data.snapshot_date is not None:
        snapshot_date = pd.to_datetime(config.data.snapshot_date)
    else:
        snapshot_date = df_filtered["InvoiceDate"].max() + pd.Timedelta(days=1)

    logger.info(f"Computing RFM summary using snapshot date: {snapshot_date.date()}")

    # Compute both feature sets
    standard_rfm = compute_standard_rfm(df_filtered, snapshot_date)
    lifetimes_rfm = compute_lifetimes_rfm(df_filtered, snapshot_date)

    # Combine metrics
    rfm_combined = standard_rfm.join(lifetimes_rfm, how="inner")

    # Save output
    output_dir = config.data.processed_path
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "02_rfm_features.csv")
    rfm_combined.to_csv(output_path, index=True)

    logger.info(
        f"RFM feature engineering complete. "
        f"Saved {len(rfm_combined)} customer summaries to {output_path}"
    )
    return rfm_combined


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    engineer_features(cfg)
