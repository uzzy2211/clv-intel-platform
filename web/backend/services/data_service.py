"""
data_service.py — Data Loading & Caching Service

Loads all processed ML pipeline outputs at startup and provides
fast in-memory access to the dashboard API endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# Resolve project root dynamically so src/ imports work
_curr = os.path.dirname(os.path.abspath(__file__))
while True:
    if os.path.exists(os.path.join(_curr, "config.yaml")):
        ROOT = _curr
        break
    _parent = os.path.dirname(_curr)
    if _parent == _curr:
        ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        break
    _curr = _parent

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


logger = logging.getLogger(__name__)

# Segment color palette — unique per segment name
SEGMENT_COLORS: Dict[str, str] = {
    "Champions": "#00ff88",
    "Loyal Customers": "#7c3aed",
    "At Risk": "#f59e0b",
    "Lost": "#ef4444",
    "New Customers": "#38bdf8",
    "Hibernating": "#64748b",
    "High Value Customers": "#00ff88",
    "Low Value / Lost": "#ef4444",
}
DEFAULT_COLOR = "#94a3b8"


class DataService:
    """Singleton service that holds all loaded data in memory."""

    def __init__(self) -> None:
        self.df_segments: Optional[pd.DataFrame] = None
        self.df_transactions: Optional[pd.DataFrame] = None
        self.evaluation_metrics: Dict[str, Any] = {}
        self.runs_data: Dict[str, Any] = {}
        self._loaded = False

    def load(self, config_path: str = "config.yaml") -> None:
        """Load all data files from disk into memory.

        Args:
            config_path: Path to config.yaml.
        """
        try:
            from src.config import load_config
            cfg = load_config(config_path)

            # Load customer segments
            seg_path = os.path.join(cfg.data.processed_path, "04_customer_segments.csv")
            if os.path.exists(seg_path):
                self.df_segments = pd.read_csv(seg_path, index_col="CustomerID")
                logger.info(f"Loaded {len(self.df_segments)} customer segments from {seg_path}")
            else:
                logger.warning(f"Segments file not found at {seg_path}")

            # Load transactions (synthetic or raw)
            tx_path = cfg.data.raw_path if os.path.exists(cfg.data.raw_path) else cfg.data.synthetic_path
            if os.path.exists(tx_path):
                self.df_transactions = pd.read_csv(tx_path)
                self.df_transactions["InvoiceDate"] = pd.to_datetime(
                    self.df_transactions["InvoiceDate"], errors="coerce"
                )
                self.df_transactions["TotalPrice"] = (
                    self.df_transactions["Quantity"] * self.df_transactions["UnitPrice"]
                )
                logger.info(f"Loaded {len(self.df_transactions)} transactions from {tx_path}")

            # Load evaluation metrics
            metrics_path = "models/evaluation_metrics.json"
            if os.path.exists(metrics_path):
                with open(metrics_path, encoding="utf-8") as fh:
                    self.evaluation_metrics = json.load(fh)

            # Load runs data
            runs_path = "models/runs.json"
            if os.path.exists(runs_path):
                with open(runs_path, encoding="utf-8") as fh:
                    self.runs_data = json.load(fh)

            self._loaded = True
            logger.info("DataService fully loaded.")

        except Exception as exc:
            logger.error(f"DataService load failed: {exc}", exc_info=True)

    def is_ready(self) -> bool:
        """Return True if data has been loaded successfully."""
        return self._loaded and self.df_segments is not None

    def get_segment_color(self, segment_name: str) -> str:
        """Return the hex color for a given segment name."""
        return SEGMENT_COLORS.get(segment_name, DEFAULT_COLOR)

    def get_total_revenue(self) -> float:
        """Return total historical revenue from transactions."""
        if self.df_transactions is not None:
            valid = self.df_transactions[
                (self.df_transactions["Quantity"] > 0)
                & (self.df_transactions["UnitPrice"] > 0)
                & (~self.df_transactions["InvoiceNo"].astype(str).str.startswith("C"))
            ]
            return float(valid["TotalPrice"].sum())
        if self.df_segments is not None:
            return float(
                (self.df_segments["monetary"] * self.df_segments["frequency"]).sum()
            )
        return 0.0

    def reload(self) -> None:
        """Force a full reload of all data from disk."""
        self._loaded = False
        self.load()


# Module-level singleton
_service = DataService()


def get_data_service() -> DataService:
    """Return the module-level DataService singleton."""
    return _service
