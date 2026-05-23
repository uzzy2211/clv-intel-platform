"""
run.py — CLV Intelligence Platform launcher

Starts the FastAPI + Uvicorn server from the project root.

Usage:
    python web/run.py
    python web/run.py --port 8000 --reload
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure project root is on the path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Change working directory to project root so relative paths
# (config.yaml, data/, models/) resolve correctly
os.chdir(ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="CLV Intelligence Platform")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════════╗
║         CLV Intelligence Platform  v1.0.0            ║
║  BG/NBD + Gamma-Gamma + K-Means Segmentation         ║
╠══════════════════════════════════════════════════════╣
║  URL:  http://localhost:{args.port:<28}║
║  API:  http://localhost:{args.port}/api/docs{' ' * 19}║
╚══════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "web.backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
