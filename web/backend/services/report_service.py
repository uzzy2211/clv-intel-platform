"""
report_service.py — PDF Report Generation Service

Delegates to the existing reports/generate_report.py module.
"""

from __future__ import annotations

import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = "reports/output/clv_segmentation_report.pdf"


def generate_pdf_report(output_path: str = DEFAULT_OUTPUT_PATH) -> tuple[bool, str]:
    """Generate the PDF executive summary report.

    Args:
        output_path: Destination path for the PDF file.

    Returns:
        Tuple of (success, message_or_path).
    """
    try:
        # Import directly by file path to avoid package resolution issues
        import importlib.util, os as _os
        spec = importlib.util.spec_from_file_location(
            "generate_report",
            _os.path.join(ROOT, "reports", "generate_report.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.generate_report(output_path=output_path)
        return True, output_path
    except Exception as exc:
        logger.error(f"PDF generation failed: {exc}", exc_info=True)
        return False, str(exc)
