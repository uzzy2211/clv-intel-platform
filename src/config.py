"""
config.py — Config Loader

Loads and exposes all project configuration from config.yaml via typed dataclasses.
No magic numbers or hardcoded paths should exist anywhere in the codebase;
everything must be retrieved through this module.

Example:
    >>> from src.config import load_config
    >>> cfg = load_config()
    >>> print(cfg.data.raw_path)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


# ---------------------------------------------------------------------------
# Sub-config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DataConfig:
    """Configuration for data paths and observation window.

    Attributes:
        raw_path: Relative path to the primary raw CSV dataset.
        synthetic_path: Relative path to the fallback synthetic CSV dataset.
        processed_path: Directory where cleaned / feature-engineered files are saved.
        snapshot_date: Optional explicit snapshot date (ISO string). None = auto.
        observation_months: Number of months to include in the training window.
        prediction_days: CLV prediction horizon in days.
    """

    raw_path: str
    synthetic_path: str
    processed_path: str
    snapshot_date: Optional[str]
    observation_months: int
    prediction_days: int


@dataclass
class ClusteringConfig:
    """Hyperparameters for the clustering step.

    Attributes:
        k_range: [min_k, max_k] range to evaluate for optimal number of clusters.
        algorithm: Clustering algorithm to use ('kmeans' | 'gmm').
        random_state: Random seed for reproducibility.
    """

    k_range: List[int]
    algorithm: str
    random_state: int


@dataclass
class ModelConfig:
    """Hyperparameters for probabilistic CLV models.

    Attributes:
        bgn_penalizer: L2 penalizer for the BG/NBD model.
        gg_penalizer: L2 penalizer for the Gamma-Gamma model.
        clustering: Nested clustering configuration.
    """

    bgn_penalizer: float
    gg_penalizer: float
    clustering: ClusteringConfig


@dataclass
class DashboardConfig:
    """Dashboard runtime settings.

    Attributes:
        port: TCP port for the Streamlit server.
        theme: UI theme ('light' | 'dark').
    """

    port: int
    theme: str


@dataclass
class ReportConfig:
    """Report generation settings.

    Attributes:
        output_dir: Directory where generated reports are saved.
        margin_rate: Assumed gross margin (e.g. 0.10 = 10%).
        discount_rate: Monthly discount rate for CLV NPV calculation.
    """

    output_dir: str
    margin_rate: float
    discount_rate: float


@dataclass
class Config:
    """Top-level project configuration.

    Attributes:
        data: Data ingestion and path settings.
        model: CLV model hyperparameters.
        dashboard: Streamlit dashboard settings.
        report: PDF report generation settings.
    """

    data: DataConfig
    model: ModelConfig
    dashboard: DashboardConfig
    report: ReportConfig


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_config(config_path: str = "config.yaml") -> Config:
    """Load project configuration from a YAML file and return a typed Config object.

    Args:
        config_path: Path to the YAML configuration file. Defaults to 'config.yaml'
            resolved relative to the current working directory.

    Returns:
        A fully populated Config dataclass instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        KeyError: If a required key is missing from the YAML.

    Example:
        >>> cfg = load_config()
        >>> cfg.model.bgn_penalizer
        0.001
    """
    if not os.path.isabs(config_path):
        # Resolve relative to the repository root (2 levels up from this file)
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resolved_path = os.path.join(repo_root, config_path)
        if os.path.exists(resolved_path):
            config_path = resolved_path

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path!r}")


    with open(config_path, "r", encoding="utf-8") as fh:
        raw: dict = yaml.safe_load(fh)

    clustering_cfg = ClusteringConfig(
        k_range=raw["model"]["clustering"]["k_range"],
        algorithm=raw["model"]["clustering"]["algorithm"],
        random_state=raw["model"]["clustering"]["random_state"],
    )

    return Config(
        data=DataConfig(
            raw_path=raw["data"]["raw_path"],
            synthetic_path=raw["data"].get("synthetic_path", "data/synthetic/synthetic_data.csv"),
            processed_path=raw["data"]["processed_path"],
            snapshot_date=raw["data"].get("snapshot_date"),
            observation_months=raw["data"]["observation_months"],
            prediction_days=raw["data"]["prediction_days"],
        ),
        model=ModelConfig(
            bgn_penalizer=raw["model"]["bgn_penalizer"],
            gg_penalizer=raw["model"]["gg_penalizer"],
            clustering=clustering_cfg,
        ),
        dashboard=DashboardConfig(
            port=raw["dashboard"]["port"],
            theme=raw["dashboard"]["theme"],
        ),
        report=ReportConfig(
            output_dir=raw["report"]["output_dir"],
            margin_rate=raw["report"]["margin_rate"],
            discount_rate=raw["report"]["discount_rate"],
        ),
    )
