"""
data_loader.py — Data Ingestion & Cleaning

Loads, validates, cleans, and filters the transaction dataset.
Handles multiple real-world column name variants (UCI Online Retail II,
custom exports, etc.) and is robust to encoding, date, and dtype issues.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column name normalisation map
# Covers: UCI Online Retail II (Invoice/Price/Customer ID),
#         standard Online Retail (InvoiceNo/UnitPrice/CustomerID),
#         and common export variants.
# ---------------------------------------------------------------------------
_COLUMN_ALIASES: dict[str, str] = {
    # InvoiceNo variants
    "invoice":          "InvoiceNo",
    "invoice_no":       "InvoiceNo",
    "invoice no":       "InvoiceNo",
    "invoiceno":        "InvoiceNo",
    # UnitPrice variants
    "price":            "UnitPrice",
    "unit_price":       "UnitPrice",
    "unit price":       "UnitPrice",
    "unitprice":        "UnitPrice",
    # CustomerID variants
    "customer id":      "CustomerID",
    "customer_id":      "CustomerID",
    "customerid":       "CustomerID",
    "cust_id":          "CustomerID",
    "custid":           "CustomerID",
    # StockCode variants
    "stock_code":       "StockCode",
    "stock code":       "StockCode",
    "stockcode":        "StockCode",
    "item_code":        "StockCode",
    # InvoiceDate variants
    "invoice_date":     "InvoiceDate",
    "invoice date":     "InvoiceDate",
    "invoicedate":      "InvoiceDate",
    "date":             "InvoiceDate",
    "transaction_date": "InvoiceDate",
    # Quantity variants
    "qty":              "Quantity",
    "quantity":         "Quantity",
    # Description variants
    "description":      "Description",
    "product_name":     "Description",
    "item_description": "Description",
    # Country variants
    "country":          "Country",
    "region":           "Country",
}

REQUIRED_COLS = {
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
}

# Encodings to try in order when reading CSV
_CSV_ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to the canonical schema using the alias map.

    Strips whitespace from column names and applies case-insensitive
    matching against the alias dictionary.

    Args:
        df: Raw DataFrame with potentially non-standard column names.

    Returns:
        DataFrame with columns renamed to canonical names where possible.
    """
    rename_map: dict[str, str] = {}
    for col in df.columns:
        normalised = col.strip().lower()
        if normalised in _COLUMN_ALIASES:
            canonical = _COLUMN_ALIASES[normalised]
            if col != canonical:
                rename_map[col] = canonical
                logger.info(f"Column rename: '{col}' -> '{canonical}'")

    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def validate_schema(df: pd.DataFrame) -> None:
    """Validate that the DataFrame has all required columns after normalisation.

    Args:
        df: Normalised DataFrame.

    Raises:
        ValueError: If required columns are still missing after normalisation.
    """
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns after normalisation: {sorted(missing)}. "
            f"Found columns: {sorted(df.columns.tolist())}. "
            f"Accepted aliases: {sorted(_COLUMN_ALIASES.keys())}"
        )


def _read_csv_robust(path: str) -> pd.DataFrame:
    """Read a CSV file trying multiple encodings until one succeeds.

    Args:
        path: Path to the CSV file.

    Returns:
        Parsed DataFrame.

    Raises:
        ValueError: If no encoding succeeds.
    """
    last_err: Optional[Exception] = None
    for enc in _CSV_ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            logger.info(f"CSV loaded with encoding '{enc}': {path}")
            return df
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            logger.debug(f"Encoding '{enc}' failed for {path}: {e}")
        except Exception as e:
            raise e
    raise ValueError(f"Could not decode CSV with any of {_CSV_ENCODINGS}: {last_err}")


def _read_excel_robust(path: str) -> pd.DataFrame:
    """Read an Excel file, trying both sheet 0 and 'Year 2009-2010' (UCI).

    Args:
        path: Path to the XLSX/XLS file.

    Returns:
        Parsed DataFrame.
    """
    # UCI Online Retail II has two sheets — try to combine them
    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
        sheets = xl.sheet_names
        logger.info(f"Excel sheets found: {sheets}")

        if len(sheets) == 1:
            df = pd.read_excel(path, sheet_name=0, engine="openpyxl")
        else:
            # Read all sheets and concatenate (UCI has Year 2009-2010 and Year 2010-2011)
            frames = []
            for sheet in sheets:
                try:
                    frame = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
                    frames.append(frame)
                    logger.info(f"  Sheet '{sheet}': {len(frame)} rows")
                except Exception as e:
                    logger.warning(f"  Could not read sheet '{sheet}': {e}")
            if not frames:
                raise ValueError("No readable sheets found in Excel file.")
            df = pd.concat(frames, ignore_index=True)
            logger.info(f"Combined {len(sheets)} sheets: {len(df)} total rows")

        return df
    except Exception as e:
        # Fallback: try xlrd for older .xls files
        logger.warning(f"openpyxl failed ({e}), trying xlrd...")
        return pd.read_excel(path, engine="xlrd")


def load_raw_file(path: str) -> pd.DataFrame:
    """Load a CSV or Excel file from disk into a DataFrame.

    Handles encoding detection, multi-sheet Excel, and column normalisation.

    Args:
        path: Absolute or relative path to the data file.

    Returns:
        Normalised DataFrame ready for cleaning.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed or schema is invalid.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    logger.info(f"Loading file: {path} ({os.path.getsize(path)/1024/1024:.1f} MB)")

    if ext == ".csv":
        df = _read_csv_robust(path)
    elif ext in (".xlsx", ".xls"):
        df = _read_excel_robust(path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    logger.info(f"Raw file loaded: {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Raw columns: {df.columns.tolist()}")

    # Normalise column names
    df = _normalise_columns(df)

    # Validate schema
    validate_schema(df)

    return df


def load_transaction_data(config: Config) -> pd.DataFrame:
    """Load the transaction dataset from raw or fallback synthetic CSV paths.

    Args:
        config: The application Config dataclass instance.

    Returns:
        A validated pandas DataFrame containing raw transaction records.

    Example:
        >>> cfg = load_config()
        >>> df = load_transaction_data(cfg)
    """
    path_to_load = config.data.raw_path

    if not os.path.exists(path_to_load):
        logger.warning(f"Raw data not found at '{path_to_load}'. Falling back to synthetic path.")
        path_to_load = config.data.synthetic_path

        if not os.path.exists(path_to_load):
            logger.warning(f"Synthetic data not found at '{path_to_load}'. Generating dataset...")
            from data.synthetic.generate_synthetic_data import generate_synthetic_data
            generate_synthetic_data(output_path=path_to_load)

    return load_raw_file(path_to_load)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean transaction data by removing invalid records and parsing types.

    Robust to mixed-type columns, unparseable dates, and non-numeric
    Quantity/UnitPrice values. Never raises on individual bad rows —
    they are dropped and logged instead.

    Args:
        df: The raw input DataFrame (already column-normalised).

    Returns:
        A cleaned copy of the DataFrame with TotalPrice added.

    Example:
        >>> df_cleaned = clean_data(df)
    """
    df_clean = df.copy()
    initial_rows = len(df_clean)
    logger.info(f"Starting data cleaning. Initial row count: {initial_rows}")

    # ── 1. Drop null CustomerID ────────────────────────────────────
    df_clean = df_clean.dropna(subset=["CustomerID"])
    logger.info(f"After dropping null CustomerID: {len(df_clean)} rows "
                f"(dropped {initial_rows - len(df_clean)})")

    # ── 2. Cast InvoiceNo to string, remove cancellations ─────────
    df_clean["InvoiceNo"] = df_clean["InvoiceNo"].astype(str).str.strip()
    before = len(df_clean)
    df_clean = df_clean[~df_clean["InvoiceNo"].str.upper().str.startswith("C", na=False)]
    logger.info(f"After removing cancellations: {len(df_clean)} rows (dropped {before - len(df_clean)})")

    # ── 3. Coerce Quantity and UnitPrice to numeric ────────────────
    df_clean["Quantity"]  = pd.to_numeric(df_clean["Quantity"],  errors="coerce")
    df_clean["UnitPrice"] = pd.to_numeric(df_clean["UnitPrice"], errors="coerce")

    # Drop rows where coercion produced NaN
    before = len(df_clean)
    df_clean = df_clean.dropna(subset=["Quantity", "UnitPrice"])
    logger.info(f"After coercing numeric cols: {len(df_clean)} rows (dropped {before - len(df_clean)} non-numeric)")

    # ── 4. Filter non-positive values ─────────────────────────────
    before = len(df_clean)
    df_clean = df_clean[(df_clean["Quantity"] > 0) & (df_clean["UnitPrice"] > 0)]
    logger.info(f"After positive filter: {len(df_clean)} rows (dropped {before - len(df_clean)})")

    # ── 5. Parse InvoiceDate — multi-format robust parsing ────────
    # Preserve raw strings for retry pass
    raw_dates = df_clean["InvoiceDate"].astype(str)

    # pandas 2.x: format="mixed" handles heterogeneous date strings
    # Fall back to errors="coerce" so bad values become NaT instead of crashing
    try:
        df_clean["InvoiceDate"] = pd.to_datetime(raw_dates, errors="coerce", format="mixed", dayfirst=False)
    except TypeError:
        # pandas < 2.0 doesn't support format="mixed"
        df_clean["InvoiceDate"] = pd.to_datetime(raw_dates, errors="coerce", dayfirst=False)

    # Second pass: European day-first format for any remaining NaT rows
    nat_mask = df_clean["InvoiceDate"].isna()
    if nat_mask.any():
        try:
            retry = pd.to_datetime(raw_dates[nat_mask], errors="coerce", format="mixed", dayfirst=True)
        except TypeError:
            retry = pd.to_datetime(raw_dates[nat_mask], errors="coerce", dayfirst=True)
        df_clean.loc[nat_mask, "InvoiceDate"] = retry

    before = len(df_clean)
    df_clean = df_clean.dropna(subset=["InvoiceDate"])
    logger.info(f"After date parsing: {len(df_clean)} rows (dropped {before - len(df_clean)} unparseable dates)")

    # ── 6. Compute TotalPrice ──────────────────────────────────────
    df_clean["TotalPrice"] = df_clean["Quantity"] * df_clean["UnitPrice"]

    # ── 7. Ensure CustomerID is numeric ───────────────────────────
    df_clean["CustomerID"] = pd.to_numeric(df_clean["CustomerID"], errors="coerce")
    before = len(df_clean)
    df_clean = df_clean.dropna(subset=["CustomerID"])
    logger.info(f"After numeric CustomerID: {len(df_clean)} rows (dropped {before - len(df_clean)})")

    if len(df_clean) == 0:
        raise ValueError(
            "No valid rows remain after cleaning. "
            "Check that your dataset has positive Quantity/UnitPrice, "
            "valid CustomerIDs, and parseable InvoiceDate values."
        )

    logger.info(
        f"Data cleaning complete. Final: {len(df_clean)} rows "
        f"(total dropped: {initial_rows - len(df_clean)})"
    )
    return df_clean


def filter_by_observation_window(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """Filter transactions to only include records within the observation window.

    The window extends backwards from the snapshot date by the configured
    number of observation months. If the filtered result is too small to
    fit models, the window is expanded automatically.

    Args:
        df: The cleaned transaction DataFrame.
        config: The application Config dataclass instance.

    Returns:
        A filtered copy of the DataFrame.

    Example:
        >>> df_filtered = filter_by_observation_window(df_cleaned, cfg)
    """
    df_filtered = df.copy()

    # Determine snapshot date
    if config.data.snapshot_date is not None:
        snapshot_date = pd.to_datetime(config.data.snapshot_date)
    else:
        snapshot_date = df_filtered["InvoiceDate"].max() + pd.Timedelta(days=1)

    # Calculate starting date
    start_date = snapshot_date - pd.DateOffset(months=config.data.observation_months)
    logger.info(f"Observation window: [{start_date.date()} → {snapshot_date.date()})")

    result = df_filtered[
        (df_filtered["InvoiceDate"] >= start_date)
        & (df_filtered["InvoiceDate"] < snapshot_date)
    ]

    logger.info(
        f"Filtered {len(df_filtered)} → {len(result)} rows "
        f"({config.data.observation_months}-month window)"
    )

    # Safety: if too few unique customers remain, expand to full dataset
    min_customers = 50
    unique_customers = result["CustomerID"].nunique()
    if unique_customers < min_customers:
        logger.warning(
            f"Only {unique_customers} customers in observation window "
            f"(minimum {min_customers}). Using full dataset instead."
        )
        result = df_filtered.copy()
        logger.info(f"Expanded to full dataset: {len(result)} rows, "
                    f"{result['CustomerID'].nunique()} customers")

    return result
