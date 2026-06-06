#!/usr/bin/env python3
"""Benchmark the list-cinemas query through the full stack."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from marquise.infrastructure.di.container import Container


async def run_benchmark(name_filter: str | None = None, iterations: int = 10) -> None:
    container = Container()

    t0 = time.perf_counter()
    await container.initialize()
    init_time = time.perf_counter() - t0

    times: list[float] = []
    for i in range(iterations):
        t0 = time.perf_counter()
        result = await container.cinema_controller.list(name=name_filter)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        print(
            f"  Run {i + 1:2d}: {elapsed * 1000:7.2f} ms"
            f"  ({len(result.cinemas)} cinemas)"
        )

    await container.shutdown()

    total = sum(times)
    avg = total / len(times)

    print()
    print(f"Filter:        {name_filter or '(none)'}")
    print(f"Iterations:    {iterations}")
    print(f"Init time:     {init_time * 1000:8.2f} ms")
    print(f"Total query:   {total * 1000:8.2f} ms")
    print(f"Min query:     {min(times) * 1000:8.2f} ms")
    print(f"Max query:     {max(times) * 1000:8.2f} ms")
    print(f"Avg query:     {avg * 1000:8.2f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark list-cinemas query end-to-end"
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        help="Optional name filter (case-insensitive)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of query runs (default: 10)",
    )
    args = parser.parse_args()

    asyncio.run(run_benchmark(name_filter=args.name, iterations=args.iterations))


if __name__ == "__main__":
    main()
