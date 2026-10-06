"""Profile repeated offline multi-agent requests without running on import."""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import pstats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from demo_system import create_demo_system


async def run_system(requests: int) -> None:
    system = create_demo_system()
    for index in range(requests):
        result = await system.process(f"Test request {index}: analyze revenue and create chart")
        if result["status"] != "success":
            raise RuntimeError(f"request {index} failed: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--limit", type=int, default=20, help="number of functions to display")
    args = parser.parse_args()
    if args.requests < 1 or args.limit < 1:
        parser.error("--requests and --limit must be positive")
    profiler = cProfile.Profile()
    profiler.runcall(lambda: asyncio.run(run_system(args.requests)))
    pstats.Stats(profiler).sort_stats("cumulative").print_stats(args.limit)


if __name__ == "__main__":
    main()
