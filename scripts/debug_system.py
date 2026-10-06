"""Run one offline multi-agent request with detailed logs."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from demo_system import create_demo_system


async def debug_request(request: str, system: Any = None) -> dict[str, Any]:
    """Process one request and print a compact debugging summary."""
    system = system or create_demo_system()
    print(f"Debugging: {request}")
    print("-" * 50)
    result = await system.process(request)
    print(f"Status: {result['status']}")
    print(f"Data: {str(result.get('data', 'N/A'))[:200]}")
    print(f"Code: {str(result.get('code', 'N/A'))[:200]}")
    print(f"Evaluation: {str(result.get('evaluation', 'N/A'))[:200]}")
    if result.get("errors"):
        print(f"Errors: {result['errors']}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", default="Analyze Q3 sales and create report")
    parser.add_argument("--log-level", default="DEBUG", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(debug_request(args.request))


if __name__ == "__main__":
    main()
