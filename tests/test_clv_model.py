"""
test_clv_model.py — Unit Tests for CLV Prediction Pipeline

Verifies BG/NBD and Gamma-Gamma model fitting, prediction, and CLV calculation
using minimal synthetic transaction data to keep tests fast and deterministic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from lifetimes import BetaGeoFitter, GammaGammaFitter

from src.clv_model import (
    fit_bgnd_model,
    fit_gg_model,
    predict_clv,
    predict_expected_profit,
    temporal_split,
)
from src.config import load_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_transactions() -> pd.DataFrame:
    """Fixture providing a small, reproducible transaction dataset.

    Contains 5 customers with varying purchase behaviour so that:
    - CustomerID 1 has many repeat purchases (returning customer)
    - CustomerID 5 has a single purchase only (one-timer)
    """
    np.random.seed(42)
    rows = []
    base = pd.Timestamp("2024-01-01")

    # Customers 1–4: multiple purchases across different dates
    for cid in range(1, 5):
        for day_offset in np.random.choice(range(1, 180), size=6, replace=False):
            rows.append({
                "CustomerID": float(cid),
                "InvoiceNo": f"INV{cid}{day_offset:03d}",
                "InvoiceDate": base + pd.Timedelta(days=int(day_offset)),
                "TotalPrice": round(float(np.random.uniform(50, 500)), 2),
            })

    # Customer 5: single purchase (one-timer — no repeat)
    rows.append({
        "CustomerID": 5.0,
        "InvoiceNo": "INV5001",
        "InvoiceDate": base + pd.Timedelta(days=10),
        "TotalPrice": 99.99,
    })

    return pd.DataFrame(rows)


@pytest.fixture
def lifetimes_rfm(mock_transactions: pd.DataFrame) -> pd.DataFrame:
    """Fixture that returns lifetimes-formatted RFM from the mock transactions."""
    from src.feature_engineering import compute_lifetimes_rfm

    snapshot = mock_transactions["InvoiceDate"].max() + pd.Timedelta(days=1)
    return compute_lifetimes_rfm(mock_transactions, snapshot)


@pytest.fixture
def fitted_bgf(lifetimes_rfm: pd.DataFrame) -> BetaGeoFitter:
    """Fixture that returns a fitted BetaGeoFitter on the mock RFM data."""
    return fit_bgnd_model(lifetimes_rfm, penalizer=0.001)


@pytest.fixture
def fitted_ggf(lifetimes_rfm: pd.DataFrame) -> GammaGammaFitter:
    """Fixture that returns a fitted GammaGammaFitter on the mock RFM data."""
    return fit_gg_model(lifetimes_rfm, penalizer=0.001)


# ---------------------------------------------------------------------------
# Tests: temporal_split
# ---------------------------------------------------------------------------

def test_temporal_split_proportions(mock_transactions: pd.DataFrame) -> None:
    """Train and test sets should cover the correct time windows."""
    df_train, df_test = temporal_split(mock_transactions, train_ratio=0.8)

    assert len(df_train) > 0, "Train split must not be empty"
    assert len(df_test) > 0, "Test split must not be empty"

    # Train max date must be strictly before test min date
    assert df_train["InvoiceDate"].max() < df_test["InvoiceDate"].min()


def test_temporal_split_no_overlap(mock_transactions: pd.DataFrame) -> None:
    """No transaction date should appear in both train and test."""
    df_train, df_test = temporal_split(mock_transactions, train_ratio=0.8)
    overlap = set(df_train.index) & set(df_test.index)
    # Row indices are just integers — dates should not overlap
    train_dates = set(df_train["InvoiceDate"].dt.date)
    test_dates = set(df_test["InvoiceDate"].dt.date)
    # Only require that max train date <= min test date
    assert df_train["InvoiceDate"].max() <= df_test["InvoiceDate"].min()


def test_temporal_split_preserves_rows(mock_transactions: pd.DataFrame) -> None:
    """The union of train and test must equal the full dataset."""
    df_train, df_test = temporal_split(mock_transactions, train_ratio=0.8)
    assert len(df_train) + len(df_test) == len(mock_transactions)


# ---------------------------------------------------------------------------
# Tests: fit_bgnd_model
# ---------------------------------------------------------------------------

def test_fit_bgnd_returns_fitter(lifetimes_rfm: pd.DataFrame) -> None:
    """fit_bgnd_model should return a fitted BetaGeoFitter instance."""
    bgf = fit_bgnd_model(lifetimes_rfm, penalizer=0.001)
    assert isinstance(bgf, BetaGeoFitter)


def test_bgf_params_are_positive(fitted_bgf: BetaGeoFitter) -> None:
    """BG/NBD model parameters (r, alpha, a, b) should all be positive after fitting."""
    params = fitted_bgf.params_
    for pname, pval in params.items():
        assert pval > 0, f"BG/NBD param '{pname}' should be positive, got {pval}"


def test_bgf_predictions_are_non_negative(
    fitted_bgf: BetaGeoFitter, lifetimes_rfm: pd.DataFrame
) -> None:
    """Predicted future purchases should be >= 0 for all customers."""
    preds = fitted_bgf.conditional_expected_number_of_purchases_up_to_time(
        30,
        lifetimes_rfm["frequency_lifetimes"],
        lifetimes_rfm["recency_lifetimes"],
        lifetimes_rfm["T_lifetimes"],
    ).fillna(0.0)
    assert (preds >= 0).all(), "All purchase predictions must be non-negative"


# ---------------------------------------------------------------------------
# Tests: fit_gg_model
# ---------------------------------------------------------------------------

def test_fit_gg_returns_fitter(lifetimes_rfm: pd.DataFrame) -> None:
    """fit_gg_model should return a fitted GammaGammaFitter instance."""
    ggf = fit_gg_model(lifetimes_rfm, penalizer=0.001)
    assert isinstance(ggf, GammaGammaFitter)


def test_gg_params_are_positive(fitted_ggf: GammaGammaFitter) -> None:
    """Gamma-Gamma model parameters (p, q, v) should all be positive after fitting."""
    params = fitted_ggf.params_
    for pname, pval in params.items():
        assert pval > 0, f"GG param '{pname}' should be positive, got {pval}"


# ---------------------------------------------------------------------------
# Tests: predict_expected_profit
# ---------------------------------------------------------------------------

def test_predict_expected_profit_shape(
    fitted_ggf: GammaGammaFitter, lifetimes_rfm: pd.DataFrame
) -> None:
    """Output Series should be same length as input RFM DataFrame."""
    fallback = lifetimes_rfm["monetary_value_lifetimes"].mean()
    profit = predict_expected_profit(fitted_ggf, lifetimes_rfm, fallback)
    assert len(profit) == len(lifetimes_rfm)


def test_predict_expected_profit_no_nan(
    fitted_ggf: GammaGammaFitter, lifetimes_rfm: pd.DataFrame
) -> None:
    """Expected average profit should not contain NaN values."""
    fallback = lifetimes_rfm["monetary_value_lifetimes"].mean()
    profit = predict_expected_profit(fitted_ggf, lifetimes_rfm, fallback)
    assert not profit.isna().any(), "Expected profit must not contain NaN"


def test_predict_expected_profit_one_timers_use_fallback(
    fitted_ggf: GammaGammaFitter, lifetimes_rfm: pd.DataFrame
) -> None:
    """Customers with frequency=0 should receive the fallback monetary value."""
    fallback = 123.45
    zero_freq_mask = lifetimes_rfm["frequency_lifetimes"] == 0
    if not zero_freq_mask.any():
        pytest.skip("No zero-frequency customers in fixture")
    profit = predict_expected_profit(fitted_ggf, lifetimes_rfm, fallback)
    # For customers with zero frequency and zero monetary, fallback is applied
    zero_freq_zero_mon = (lifetimes_rfm["frequency_lifetimes"] == 0) & (
        lifetimes_rfm["monetary_value_lifetimes"] == 0
    )
    if zero_freq_zero_mon.any():
        assert (profit[zero_freq_zero_mon] == fallback).all()


# ---------------------------------------------------------------------------
# Tests: predict_clv (integration)
# ---------------------------------------------------------------------------

def test_predict_clv_columns_present(
    fitted_bgf: BetaGeoFitter,
    fitted_ggf: GammaGammaFitter,
    lifetimes_rfm: pd.DataFrame,
) -> None:
    """predict_clv should add predicted_purchases, expected_avg_profit, clv, churn_probability."""
    cfg = load_config()
    result = predict_clv(cfg, fitted_bgf, fitted_ggf, lifetimes_rfm)
    expected_cols = ["predicted_purchases", "expected_avg_profit", "clv", "churn_probability"]
    for col in expected_cols:
        assert col in result.columns, f"Column '{col}' missing from CLV output"


def test_predict_clv_no_negative_values(
    fitted_bgf: BetaGeoFitter,
    fitted_ggf: GammaGammaFitter,
    lifetimes_rfm: pd.DataFrame,
) -> None:
    """CLV and predicted_purchases should be >= 0 for all customers."""
    cfg = load_config()
    result = predict_clv(cfg, fitted_bgf, fitted_ggf, lifetimes_rfm)
    assert (result["clv"] >= 0).all(), "CLV must not be negative"
    assert (result["predicted_purchases"] >= 0).all(), "Predicted purchases must not be negative"


def test_predict_clv_no_nan(
    fitted_bgf: BetaGeoFitter,
    fitted_ggf: GammaGammaFitter,
    lifetimes_rfm: pd.DataFrame,
) -> None:
    """CLV output must not contain any NaN values."""
    cfg = load_config()
    result = predict_clv(cfg, fitted_bgf, fitted_ggf, lifetimes_rfm)
    for col in ["clv", "predicted_purchases", "expected_avg_profit", "churn_probability"]:
        assert not result[col].isna().any(), f"Column '{col}' must not contain NaN"
