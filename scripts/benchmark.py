"""Benchmark the offline multi-agent system and save stable JSON metrics."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from demo_system import create_demo_system


class Benchmark:
    def __init__(self):
        self.results: list[dict[str, Any]] = []

    async def run_test(self, name: str, request: str, system: Any, iterations: int = 3) -> dict[str, Any]:
        """Run one request repeatedly and collect latency plus success metrics."""
        if iterations < 1:
            raise ValueError("iterations must be at least one")
        print(f"\nBenchmarking: {name}")
        latencies: list[float] = []
        successes = 0
        for index in range(iterations):
            started = perf_counter()
            result = await system.process(request)
            latency = perf_counter() - started
            latencies.append(latency)
            succeeded = result.get("status") == "success"
            successes += succeeded
            print(f"  Iteration {index + 1}: {latency:.4f}s {'PASS' if succeeded else 'FAIL'}")
        stats = {
            "name": name,
            "iterations": iterations,
            "successes": successes,
            "success_rate": round(successes / iterations, 4),
            "min_seconds": min(latencies),
            "max_seconds": max(latencies),
            "avg_seconds": sum(latencies) / iterations,
            "median_seconds": median(latencies),
        }
        self.results.append(stats)
        print(f"  Summary: avg={stats['avg_seconds']:.4f}s success={successes}/{iterations}")
        return stats


async def run_benchmarks(iterations: int) -> list[dict[str, Any]]:
    system = create_demo_system()
    benchmark = Benchmark()
    for name, request in [
        ("Simple data query", "What is total revenue?"),
        ("Code generation", "Write Python script to read CSV"),
        ("Complex workflow", "Analyze sales data AND create chart AND evaluate result"),
    ]:
        await benchmark.run_test(name, request, system, iterations)
    return benchmark.results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("results") / "benchmark_results.json")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least one")
    results = asyncio.run(run_benchmarks(args.iterations))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nBenchmark complete. Results saved to {args.output}")


if __name__ == "__main__":
    main()
