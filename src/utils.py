"""
utils.py — Shared Helpers

Provides utility functions for logging setup, JSON run tracking,
and file loading used across multiple components.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure central logging style.

    Args:
        level: Log level (e.g. logging.INFO).

    Example:
        >>> setup_logging(logging.DEBUG)
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def save_run_record(record_path: str, record_data: Dict[str, Any]) -> None:
    """Save or append run parameters and metrics to a JSON record file.

    Args:
        record_path: Path to the target JSON file.
        record_data: Data payload to save.

    Example:
        >>> save_run_record("models/runs.json", run_data)
    """
    history = []
    if os.path.exists(record_path):
        try:
            with open(record_path, "r", encoding="utf-8") as fh:
                history = json.load(fh)
                if not isinstance(history, list):
                    history = [history]
        except json.JSONDecodeError:
            logger.warning(f"Error reading JSON from {record_path}. Overwriting.")

    history.append(record_data)

    os.makedirs(os.path.dirname(record_path), exist_ok=True)
    with open(record_path, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2)

    logger.info(f"Appended run record to {record_path}")
