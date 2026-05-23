"""
clv_model.py — CLV Prediction Pipeline (BG/NBD + Gamma-Gamma)

Fits probabilistic models to predict expected future purchases and average transaction value,
combines them to estimate Customer Lifetime Value (CLV), and evaluates the model's accuracy
on a temporal test split.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import _customer_lifetime_value as customer_lifetime_value

from src.config import Config, load_config
from src.data_loader import clean_data, load_transaction_data
from src.feature_engineering import compute_lifetimes_rfm, compute_standard_rfm

logger = logging.getLogger(__name__)


def temporal_split(df: pd.DataFrame, train_ratio: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Perform a temporal split on transaction data.

    Args:
        df: Cleaned transaction DataFrame.
        train_ratio: Proportion of time window to assign to training.

    Returns:
        Tuple of (train_df, test_df).

    Example:
        >>> df_train, df_test = temporal_split(df_clean, 0.8)
    """
    df_sorted = df.sort_values("InvoiceDate")
    min_date = df_sorted["InvoiceDate"].min()
    max_date = df_sorted["InvoiceDate"].max()
    duration = max_date - min_date
    split_date = min_date + duration * train_ratio

    df_train = df_sorted[df_sorted["InvoiceDate"] < split_date].copy()
    df_test = df_sorted[df_sorted["InvoiceDate"] >= split_date].copy()

    logger.info(
        f"Temporal split at {split_date.date()}. "
        f"Train records: {len(df_train)}, Test records: {len(df_test)}"
    )
    return df_train, df_test


def fit_bgnd_model(rfm_df: pd.DataFrame, penalizer: float) -> BetaGeoFitter:
    """Fit the Beta-Geometric / Negative Binomial Distribution model.

    Automatically retries with escalating penalizer coefficients if the
    initial fit fails to converge. This handles large, sparse, or
    high-variance retail datasets without crashing the pipeline.

    Args:
        rfm_df: DataFrame containing lifetimes RFM features.
        penalizer: Starting L2 regularization penalizer (from config).

    Returns:
        A fitted BetaGeoFitter.

    Raises:
        RuntimeError: If the model fails to converge at all penalizer levels.

    Example:
        >>> bgf = fit_bgnd_model(rfm_train, 0.5)
    """
    # Escalation ladder — try config value first, then progressively stronger
    candidates = sorted({penalizer, 0.1, 0.5, 1.0, 5.0, 10.0})

    last_exc: Exception = RuntimeError("BG/NBD fit never attempted.")

    for coef in candidates:
        try:
            logger.info(f"Fitting BG/NBD model with penalizer_coef={coef}")
            bgf = BetaGeoFitter(penalizer_coef=coef)
            bgf.fit(
                rfm_df["frequency_lifetimes"],
                rfm_df["recency_lifetimes"],
                rfm_df["T_lifetimes"],
            )
            if coef != penalizer:
                logger.warning(
                    f"BG/NBD converged at penalizer_coef={coef} "
                    f"(config value {penalizer} failed). "
                    "Consider updating bgn_penalizer in config.yaml."
                )
            else:
                logger.info(f"BG/NBD converged at penalizer_coef={coef}")
            return bgf
        except Exception as exc:
            logger.warning(f"BG/NBD did not converge at penalizer_coef={coef}: {exc}")
            last_exc = exc

    raise RuntimeError(
        f"BG/NBD model failed to converge at all penalizer levels "
        f"({[str(c) for c in candidates]}). "
        f"Last error: {last_exc}. "
        "Check that your dataset has sufficient repeat-purchase history "
        "(at least 6 months, multiple transactions per customer)."
    )


def fit_gg_model(rfm_df: pd.DataFrame, penalizer: float) -> GammaGammaFitter:
    """Fit the Gamma-Gamma model on returning customers.

    Automatically retries with escalating penalizer coefficients if the
    initial fit fails to converge.

    Args:
        rfm_df: DataFrame containing lifetimes RFM features.
        penalizer: Starting L2 regularization penalizer (from config).

    Returns:
        A fitted GammaGammaFitter.

    Raises:
        ValueError: If no repeat customers exist in the dataset.
        RuntimeError: If the model fails to converge at all penalizer levels.

    Example:
        >>> ggf = fit_gg_model(rfm_train, 0.5)
    """
    returning = rfm_df[
        (rfm_df["frequency_lifetimes"] > 0) & (rfm_df["monetary_value_lifetimes"] > 0)
    ].copy()

    if len(returning) == 0:
        raise ValueError(
            "No repeat customers found to fit the Gamma-Gamma model. "
            "The dataset may be too sparse or the observation window too narrow. "
            "Ensure your dataset spans at least 6 months and has customers with 2+ purchases."
        )

    logger.info(f"Gamma-Gamma: {len(returning)} repeat customers available for fitting.")

    # Escalation ladder — try config value first, then progressively stronger
    candidates = sorted({penalizer, 0.1, 0.5, 1.0, 5.0, 10.0})

    # For very small repeat-customer sets, start at a higher floor
    if len(returning) < 10:
        logger.warning(
            f"Only {len(returning)} repeat customers — raising minimum penalizer to 1.0."
        )
        candidates = sorted({c for c in candidates if c >= 1.0} | {1.0})

    last_exc: Exception = RuntimeError("Gamma-Gamma fit never attempted.")

    for coef in candidates:
        try:
            logger.info(f"Fitting Gamma-Gamma model with penalizer_coef={coef}")
            ggf = GammaGammaFitter(penalizer_coef=coef)
            ggf.fit(returning["frequency_lifetimes"], returning["monetary_value_lifetimes"])
            if coef != penalizer:
                logger.warning(
                    f"Gamma-Gamma converged at penalizer_coef={coef} "
                    f"(config value {penalizer} failed). "
                    "Consider updating gg_penalizer in config.yaml."
                )
            else:
                logger.info(f"Gamma-Gamma converged at penalizer_coef={coef}")
            return ggf
        except Exception as exc:
            logger.warning(f"Gamma-Gamma did not converge at penalizer_coef={coef}: {exc}")
            last_exc = exc

    raise RuntimeError(
        f"Gamma-Gamma model failed to converge at all penalizer levels "
        f"({[str(c) for c in candidates]}). "
        f"Last error: {last_exc}."
    )


def predict_expected_profit(
    ggf: GammaGammaFitter, rfm_df: pd.DataFrame, fallback_val: float
) -> pd.Series:
    """Predict expected average profit with a fallback for first-time buyers.

    Args:
        ggf: Fitted GammaGammaFitter.
        rfm_df: Lifetimes RFM DataFrame.
        fallback_val: Global average monetary value as a fallback.

    Returns:
        Series of expected average profit per customer.

    Example:
        >>> profit = predict_expected_profit(ggf, rfm_df, global_mean)
    """
    # Fitters conditional_expected_average_profit requires positive frequency/monetary values
    valid_mask = (rfm_df["frequency_lifetimes"] > 0) & (rfm_df["monetary_value_lifetimes"] > 0)

    # Initialize with historical monetary value or fallback
    expected_profit = rfm_df["monetary_value_lifetimes"].copy()
    expected_profit = expected_profit.where(expected_profit > 0, fallback_val)

    if valid_mask.any():
        preds = ggf.conditional_expected_average_profit(
            rfm_df.loc[valid_mask, "frequency_lifetimes"],
            rfm_df.loc[valid_mask, "monetary_value_lifetimes"],
        )
        expected_profit.loc[valid_mask] = preds

    return expected_profit


def predict_clv(
    config: Config,
    bgf: BetaGeoFitter,
    ggf: GammaGammaFitter,
    rfm_df: pd.DataFrame,
) -> pd.DataFrame:
    """Predict future purchases, expected average profit, and CLV.

    Args:
        config: Central configuration.
        bgf: Fitted BG/NBD model.
        ggf: Fitted Gamma-Gamma model.
        rfm_df: Combined RFM features DataFrame.

    Returns:
        DataFrame with CLV predictions added.

    Example:
        >>> clv_df = predict_clv(cfg, bgf, ggf, rfm_df)
    """
    df = rfm_df.copy()
    prediction_days = config.data.prediction_days
    margin = config.report.margin_rate
    discount_rate = config.report.discount_rate

    # Predict expected purchases in horizon
    df["predicted_purchases"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        prediction_days,
        df["frequency_lifetimes"],
        df["recency_lifetimes"],
        df["T_lifetimes"],
    )
    df["predicted_purchases"] = df["predicted_purchases"].fillna(0.0)

    # Predict expected average profit (fallback = average monetary_value of returning customers)
    returning_avg = df.loc[df["frequency_lifetimes"] > 0, "monetary_value_lifetimes"].mean()
    if pd.isna(returning_avg):
        returning_avg = df["monetary_value_lifetimes"].mean()

    df["expected_avg_profit"] = predict_expected_profit(ggf, df, returning_avg)

    # Use lifetimes customer_lifetime_value for NPV calculation
    # lifetimes expects time in months
    prediction_months = prediction_days / 30.0
    clv_val = customer_lifetime_value(
        transaction_prediction_model=bgf,
        frequency=df["frequency_lifetimes"],
        recency=df["recency_lifetimes"],
        T=df["T_lifetimes"],
        monetary_value=df["expected_avg_profit"],
        time=prediction_months,
        discount_rate=discount_rate,
    )
    df["clv"] = clv_val * margin
    df["clv"] = df["clv"].fillna(0.0)
    df["churn_probability"] = 1.0 - bgf.conditional_probability_alive(
        df["frequency_lifetimes"],
        df["recency_lifetimes"],
        df["T_lifetimes"],
    )
    df["churn_probability"] = df["churn_probability"].fillna(0.0)

    return df


def run_clv_pipeline(config: Config) -> pd.DataFrame:
    """Load data, fit models, predict CLV, and save artifacts.

    Args:
        config: Typed project configuration.

    Returns:
        DataFrame of customer RFM with CLV predictions.

    Example:
        >>> df_clv = run_clv_pipeline(cfg)
    """
    df_raw = load_transaction_data(config)
    df_clean = clean_data(df_raw)

    # Fit models on the full observation window
    snapshot_date = (
        pd.to_datetime(config.data.snapshot_date)
        if config.data.snapshot_date is not None
        else df_clean["InvoiceDate"].max() + pd.Timedelta(days=1)
    )

    # Calculate train RFM features
    standard_rfm = compute_standard_rfm(df_clean, snapshot_date)
    lifetimes_rfm = compute_lifetimes_rfm(df_clean, snapshot_date)
    rfm_combined = standard_rfm.join(lifetimes_rfm, how="inner")

    # Fit fitters
    bgf = fit_bgnd_model(rfm_combined, config.model.bgn_penalizer)
    ggf = fit_gg_model(rfm_combined, config.model.gg_penalizer)

    # Predict CLV
    df_predictions = predict_clv(config, bgf, ggf, rfm_combined)

    # Save outputs
    output_dir = config.data.processed_path
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "03_clv_predictions.csv")
    df_predictions.to_csv(output_path, index=True)
    logger.info(f"Saved CLV predictions to {output_path}")

    # Save models
    os.makedirs("models", exist_ok=True)
    bgf.save_model("models/bgf_model.pkl")
    ggf.save_model("models/ggf_model.pkl")
    logger.info("Saved models/bgf_model.pkl and models/ggf_model.pkl")

    return df_predictions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    run_clv_pipeline(cfg)
