"""Performance benchmark for leaderboard operations.

Generates N fake users with random scores and measures latency and
throughput for single inserts, bulk inserts, rank lookups, concurrent
increments, top-N queries, and batch deletes.

Usage:
    python -m app.utils.benchmark
    python -m app.utils.benchmark --users 10000 --lookups 2000 --workers 20
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import fakeredis

from app.config import Settings
from app.db.redis_client import reset_redis_client
from app.services.leaderboard_service import LeaderboardService
from app.utils.logger import get_logger, setup_logging

logger = get_logger("benchmark")

# Defaults; overridable via CLI args (see `_parse_args`).
USER_COUNT = 100_000
SAMPLE_LOOKUPS = 10_000
CONCURRENT_WORKERS = 50
BULK_BATCH_SIZE = 1_000
TOP_N_SAMPLES = 1_000
WARMUP_ITERATIONS = 100
RESULTS_FILE = "benchmark_results.json"
CSV_FILE = "benchmark_results.csv"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line configuration for the benchmark run."""
    parser = argparse.ArgumentParser(description="Leaderboard performance benchmark")
    parser.add_argument(
        "--users", type=int, default=USER_COUNT,
        help=f"Number of fake users to generate (default: {USER_COUNT:,})",
    )
    parser.add_argument(
        "--lookups", type=int, default=SAMPLE_LOOKUPS,
        help=f"Number of sample lookups/increments (default: {SAMPLE_LOOKUPS:,})",
    )
    parser.add_argument(
        "--workers", type=int, default=CONCURRENT_WORKERS,
        help=f"Concurrent worker threads for increments (default: {CONCURRENT_WORKERS})",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BULK_BATCH_SIZE,
        help=f"Batch size for bulk insert benchmark (default: {BULK_BATCH_SIZE:,})",
    )
    parser.add_argument(
        "--output", type=str, default=RESULTS_FILE,
        help=f"Path to write JSON results (default: {RESULTS_FILE})",
    )
    parser.add_argument(
        "--csv", type=str, default=CSV_FILE,
        help=f"Path to write CSV results, or 'none' to skip (default: {CSV_FILE})",
    )
    parser.add_argument(
        "--no-warmup", action="store_true",
        help="Skip the warm-up phase before measuring performance",
    )
    return parser.parse_args(argv)


def _percentile(data: list[float], pct: float) -> float:
    """Calculate the p-th percentile of a sorted dataset."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * pct / 100)
    index = min(index, len(sorted_data) - 1)
    return sorted_data[index]


def _safe_mean(data: list[float]) -> float:
    """Mean that tolerates empty input instead of raising."""
    return statistics.mean(data) if data else 0.0


def _warm_up(service: LeaderboardService, iterations: int = WARMUP_ITERATIONS) -> None:
    """
    Run a small number of throwaway operations before measuring.

    Connection setup, first-call caching, and JIT-ish warm effects can
    skew the very first measured latencies. This runs quietly and is
    excluded from the recorded results, then resets the leaderboard.
    """
    for i in range(iterations):
        service.set_score(f"warmup_{i:06d}", float(i))
    service.reset_leaderboard()


def _get_redis_engine_info(service: LeaderboardService) -> dict[str, str]:
    """
    Best-effort detection of the Redis engine/version in use.

    Falls back gracefully since fakeredis may not support INFO the same
    way a real Redis server does, and older fakeredis versions may not
    implement it at all.
    """
    info: dict[str, str] = {"redis_engine": type(service.redis).__module__.split(".")[0]}
    try:
        server_info = service.redis.info()
        version = server_info.get("redis_version")
        if version:
            info["redis_version"] = str(version)
    except Exception:
        # INFO not supported by this client/version; engine name alone is fine.
        pass
    return info


def _get_memory_usage(service: LeaderboardService) -> int | None:
    """
    Best-effort MEMORY USAGE lookup for the leaderboard key.

    Returns None if the command isn't supported by the connected client
    (support varies across fakeredis versions and real Redis configs).
    """
    try:
        usage = service.redis.memory_usage(service.key)
        return int(usage) if usage is not None else None
    except Exception:
        return None


def _benchmark_single_insert(service: LeaderboardService, user_count: int) -> tuple[list[float], float]:
    """Benchmark one-at-a-time set_score() calls. Returns (latencies_ms, elapsed_s)."""
    latencies: list[float] = []
    start_all = time.perf_counter()
    for i in range(user_count):
        start = time.perf_counter()
        service.set_score(f"user_{i:06d}", random.uniform(0, 1_000_000))
        latencies.append((time.perf_counter() - start) * 1000)
        if (i + 1) % 25_000 == 0:
            print(f"  Inserted {i + 1:,} / {user_count:,} users (single)...")
    elapsed = time.perf_counter() - start_all
    return latencies, elapsed


def _benchmark_bulk_insert(
    service: LeaderboardService,
    user_count: int,
    batch_size: int,
) -> tuple[list[float], list[float], float]:
    """
    Benchmark set_scores_bulk() in batches.

    Returns:
        Tuple of (per-batch latencies_ms, per-user latencies_ms, elapsed_s).
        Per-user latency is the batch latency divided by batch size, so it
        can be compared directly against single-insert per-user latency.
    """
    batch_latencies: list[float] = []
    per_user_latencies: list[float] = []
    start_all = time.perf_counter()

    for batch_start in range(0, user_count, batch_size):
        scores = {
            f"buser_{i:06d}": random.uniform(0, 1_000_000)
            for i in range(batch_start, min(batch_start + batch_size, user_count))
        }
        start = time.perf_counter()
        service.set_scores_bulk(scores)
        batch_ms = (time.perf_counter() - start) * 1000
        batch_latencies.append(batch_ms)
        per_user_latencies.append(batch_ms / len(scores))

    elapsed = time.perf_counter() - start_all
    return batch_latencies, per_user_latencies, elapsed


def _benchmark_lookups(
    service: LeaderboardService,
    user_count: int,
    sample_size: int,
) -> tuple[list[float], float]:
    """Benchmark get_rank() lookups. Returns (latencies_ms, elapsed_s)."""
    latencies: list[float] = []
    start_all = time.perf_counter()
    for _ in range(sample_size):
        username = f"user_{random.randint(0, user_count - 1):06d}"
        start = time.perf_counter()
        service.get_rank(username)
        latencies.append((time.perf_counter() - start) * 1000)
    elapsed = time.perf_counter() - start_all
    return latencies, elapsed


def _benchmark_concurrent_increments(
    service: LeaderboardService,
    user_count: int,
    sample_size: int,
    workers: int,
) -> tuple[list[float], float]:
    """Benchmark increment_score() under concurrent load. Returns (latencies_ms, elapsed_s)."""

    def _increment_task(_index: int) -> float:
        username = f"user_{random.randint(0, user_count - 1):06d}"
        start = time.perf_counter()
        service.increment_score(username, random.uniform(1, 100))
        return (time.perf_counter() - start) * 1000

    start_all = time.perf_counter()
    latencies: list[float] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_increment_task, i) for i in range(sample_size)]
        for future in as_completed(futures):
            latencies.append(future.result())
    elapsed = time.perf_counter() - start_all
    return latencies, elapsed


def _benchmark_top_players(
    service: LeaderboardService,
    samples: int,
    limit: int = 10,
) -> tuple[list[float], float]:
    """Benchmark get_top_players() queries. Returns (latencies_ms, elapsed_s)."""
    latencies: list[float] = []
    start_all = time.perf_counter()
    for _ in range(samples):
        start = time.perf_counter()
        service.get_top_players(limit)
        latencies.append((time.perf_counter() - start) * 1000)
    elapsed = time.perf_counter() - start_all
    return latencies, elapsed


def _benchmark_batch_delete(
    service: LeaderboardService,
    user_count: int,
    batch_size: int,
) -> tuple[list[float], float]:
    """Benchmark delete_users() in batches. Returns (per-batch latencies_ms, elapsed_s)."""
    latencies: list[float] = []
    start_all = time.perf_counter()

    for batch_start in range(0, user_count, batch_size):
        usernames = [
            f"buser_{i:06d}"
            for i in range(batch_start, min(batch_start + batch_size, user_count))
        ]
        start = time.perf_counter()
        service.delete_users(usernames)
        latencies.append((time.perf_counter() - start) * 1000)

    elapsed = time.perf_counter() - start_all
    return latencies, elapsed


def _run_benchmark(
    service: LeaderboardService,
    user_count: int = USER_COUNT,
    sample_lookups: int = SAMPLE_LOOKUPS,
    workers: int = CONCURRENT_WORKERS,
    batch_size: int = BULK_BATCH_SIZE,
    warm_up: bool = True,
) -> dict[str, float]:
    """
    Execute the full benchmark suite.

    Returns:
        Dictionary of latency, throughput, and environment statistics.
    """
    service.reset_leaderboard()

    engine_info = _get_redis_engine_info(service)

    print(f"\n{'=' * 60}")
    print("Redis Leaderboard Engine - Performance Benchmark")
    print(f"{'=' * 60}")
    print("Environment")
    print("-" * 40)
    print(f"  Benchmark Date : {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Python Version : {platform.python_version()}")
    print(f"  Redis Engine   : {engine_info.get('redis_engine', 'unknown')}"
          + (f" ({engine_info['redis_version']})" if "redis_version" in engine_info else ""))
    print(f"  Users Tested   : {user_count:,}")
    print(f"  Workers        : {workers}")
    print(f"  Batch Size     : {batch_size:,}")
    print(f"{'=' * 60}\n")

    if warm_up:
        print(f"Warming up ({WARMUP_ITERATIONS} operations)...\n")
        _warm_up(service)

    print(f"Generating {user_count:,} users with random scores...\n")

    # Phase 1: Single-insert baseline
    print("Phase 1: Single insert (set_score)...")
    single_latencies, single_elapsed = _benchmark_single_insert(service, user_count)
    single_ops_per_sec = user_count / single_elapsed if single_elapsed else 0.0
    print(f"  Single insert phase complete in {single_elapsed:.2f}s\n")

    # Phase 2: Bulk insert (separate key range so both datasets coexist for lookups)
    print(f"Phase 2: Bulk insert (set_scores_bulk, batch_size={batch_size:,})...")
    bulk_batch_latencies, bulk_per_user_latencies, bulk_elapsed = _benchmark_bulk_insert(
        service, user_count, batch_size
    )
    bulk_ops_per_sec = user_count / bulk_elapsed if bulk_elapsed else 0.0
    print(f"  Bulk insert phase complete in {bulk_elapsed:.2f}s\n")

    # Phase 3: Rank lookups (against the "user_*" single-insert dataset)
    print(f"Phase 3: {sample_lookups:,} rank lookups (get_rank)...")
    lookup_latencies, lookup_elapsed = _benchmark_lookups(service, user_count, sample_lookups)
    lookup_ops_per_sec = sample_lookups / lookup_elapsed if lookup_elapsed else 0.0

    # Phase 4: Concurrent increments
    print(f"Phase 4: {sample_lookups:,} concurrent increments ({workers} workers)...")
    concurrent_latencies, concurrent_elapsed = _benchmark_concurrent_increments(
        service, user_count, sample_lookups, workers
    )
    concurrent_ops_per_sec = sample_lookups / concurrent_elapsed if concurrent_elapsed else 0.0

    # Phase 5: Top-N queries
    print(f"Phase 5: {TOP_N_SAMPLES:,} top-10 queries (get_top_players)...")
    top_latencies, top_elapsed = _benchmark_top_players(service, TOP_N_SAMPLES)
    top_ops_per_sec = TOP_N_SAMPLES / top_elapsed if top_elapsed else 0.0

    # Phase 6: Batch delete (removes the "buser_*" bulk-insert dataset)
    print(f"Phase 6: Batch delete (delete_users, batch_size={batch_size:,})...")
    delete_latencies, delete_elapsed = _benchmark_batch_delete(service, user_count, batch_size)
    delete_ops_per_sec = user_count / delete_elapsed if delete_elapsed else 0.0
    print(f"  Batch delete phase complete in {delete_elapsed:.2f}s\n")

    all_latencies = single_latencies + lookup_latencies + concurrent_latencies
    improvement_factor = (
        _safe_mean(single_latencies) / _safe_mean(bulk_per_user_latencies)
        if _safe_mean(bulk_per_user_latencies) > 0
        else 0.0
    )

    memory_bytes = _get_memory_usage(service)

    results = {
        "generated_at": datetime.now().isoformat(),
        "python_version": platform.python_version(),
        **engine_info,
        "user_count": user_count,
        "workers": workers,
        "batch_size": batch_size,
        "total_operations": len(all_latencies),
        "average_ms": _safe_mean(all_latencies),
        "median_ms": statistics.median(all_latencies) if all_latencies else 0.0,
        "p95_ms": _percentile(all_latencies, 95),
        "p99_ms": _percentile(all_latencies, 99),
        "max_ms": max(all_latencies) if all_latencies else 0.0,
        "min_ms": min(all_latencies) if all_latencies else 0.0,
        # Single insert
        "single_insert_avg_ms": _safe_mean(single_latencies),
        "single_insert_ops_sec": single_ops_per_sec,
        # Bulk insert
        "bulk_insert_batch_avg_ms": _safe_mean(bulk_batch_latencies),
        "bulk_insert_avg_ms": _safe_mean(bulk_per_user_latencies),
        "bulk_insert_ops_sec": bulk_ops_per_sec,
        "bulk_insert_improvement_factor": improvement_factor,
        # Lookup
        "lookup_avg_ms": _safe_mean(lookup_latencies),
        "lookup_p95_ms": _percentile(lookup_latencies, 95),
        "lookup_p99_ms": _percentile(lookup_latencies, 99),
        "lookup_ops_sec": lookup_ops_per_sec,
        # Concurrent increment
        "concurrent_avg_ms": _safe_mean(concurrent_latencies),
        "concurrent_p95_ms": _percentile(concurrent_latencies, 95),
        "concurrent_p99_ms": _percentile(concurrent_latencies, 99),
        "concurrent_ops_sec": concurrent_ops_per_sec,
        # Top-N query
        "top10_avg_ms": _safe_mean(top_latencies),
        "top10_ops_sec": top_ops_per_sec,
        # Batch delete
        "batch_delete_avg_ms": _safe_mean(delete_latencies),
        "batch_delete_ops_sec": delete_ops_per_sec,
    }

    if memory_bytes is not None:
        results["memory_bytes"] = memory_bytes

    _print_results(results)
    return results


def _print_results(results: dict[str, float]) -> None:
    """Print a formatted, presentation-ready benchmark report."""
    print(f"\n{'=' * 60}")
    print("Redis Leaderboard Performance Report")
    print(f"{'=' * 60}")
    print("\nEnvironment")
    print("-" * 40)
    print(f"  Benchmark Date : {results.get('generated_at', 'n/a')}")
    print(f"  Python Version : {results.get('python_version', 'n/a')}")
    engine_label = results.get("redis_engine", "unknown")
    if results.get("redis_version"):
        engine_label = f"{engine_label} ({results['redis_version']})"
    print(f"  Redis Engine   : {engine_label}")
    print(f"  Users Tested   : {int(results['user_count']):,}")
    print(f"  Workers        : {int(results.get('workers', 0))}")
    print(f"  Batch Size     : {int(results.get('batch_size', 0)):,}")
    if "memory_bytes" in results:
        print(f"  Memory Usage   : {int(results['memory_bytes']):,} bytes")
    print()

    print("Single Insert")
    print("-" * 40)
    print(f"  Average Latency : {results['single_insert_avg_ms']:.4f} ms")
    print(f"  Throughput      : {results['single_insert_ops_sec']:,.2f} ops/sec\n")

    print("Bulk Insert")
    print("-" * 40)
    print(f"  Average Latency : {results['bulk_insert_avg_ms']:.4f} ms (per user)")
    print(f"  Batch Latency   : {results['bulk_insert_batch_avg_ms']:.4f} ms (per batch)")
    print(f"  Throughput      : {results['bulk_insert_ops_sec']:,.2f} ops/sec")
    print(f"  Improvement     : {results['bulk_insert_improvement_factor']:.1f}x vs single insert\n")

    print("Rank Lookup")
    print("-" * 40)
    print(f"  Average Latency : {results['lookup_avg_ms']:.4f} ms")
    print(f"  P95             : {results['lookup_p95_ms']:.4f} ms")
    print(f"  P99             : {results['lookup_p99_ms']:.4f} ms")
    print(f"  Throughput      : {results['lookup_ops_sec']:,.2f} ops/sec\n")

    print("Concurrent Increment")
    print("-" * 40)
    print(f"  Average Latency : {results['concurrent_avg_ms']:.4f} ms")
    print(f"  P95             : {results['concurrent_p95_ms']:.4f} ms")
    print(f"  P99             : {results['concurrent_p99_ms']:.4f} ms")
    print(f"  Throughput      : {results['concurrent_ops_sec']:,.2f} ops/sec\n")

    print("Top 10 Query")
    print("-" * 40)
    print(f"  Average Latency : {results['top10_avg_ms']:.4f} ms")
    print(f"  Throughput      : {results['top10_ops_sec']:,.2f} ops/sec\n")

    print("Batch Delete")
    print("-" * 40)
    print(f"  Average Latency : {results['batch_delete_avg_ms']:.4f} ms (per batch)")
    print(f"  Throughput      : {results['batch_delete_ops_sec']:,.2f} ops/sec")
    print(f"{'=' * 60}")

    print("\nOverall")
    print("-" * 40)
    print(f"  Total operations : {int(results['total_operations']):,}")
    print(f"  Average latency  : {results['average_ms']:.4f} ms")
    print(f"  Median latency   : {results['median_ms']:.4f} ms")
    print(f"  P95 latency      : {results['p95_ms']:.4f} ms")
    print(f"  P99 latency      : {results['p99_ms']:.4f} ms")

    target = 50.0
    status = "PASS" if results["p99_ms"] < target else "REVIEW"
    print(f"\n  Target P99 < {target}ms : [{status}] (actual: {results['p99_ms']:.4f} ms)")
    print()


def _export_results(results: dict[str, float], output_path: str) -> None:
    """Write benchmark results to a JSON file for reporting/documentation."""
    try:
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=4)
        print(f"Results exported to {output_path}")
    except OSError as exc:
        logger.error("Failed to write benchmark results to %s: %s", output_path, exc)


def _export_results_csv(results: dict[str, float], output_path: str) -> None:
    """
    Write benchmark results to a flat CSV file (metric, value per row).

    A flat key/value layout is used rather than a single wide row so the
    file stays readable regardless of how many metrics are added later.
    """
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["metric", "value"])
            for key, value in results.items():
                writer.writerow([key, value])
        print(f"Results exported to {output_path}")
    except OSError as exc:
        logger.error("Failed to write benchmark CSV to %s: %s", output_path, exc)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the benchmark script."""
    args = _parse_args(argv)
    setup_logging("WARNING")

    fake_server = fakeredis.FakeStrictRedis(decode_responses=True)
    reset_redis_client(client=fake_server)

    settings = Settings(redis_leaderboard_key="leaderboard:benchmark")
    service = LeaderboardService(redis_client=fake_server, settings=settings)

    try:
        results = _run_benchmark(
            service,
            user_count=args.users,
            sample_lookups=args.lookups,
            workers=args.workers,
            batch_size=args.batch_size,
            warm_up=not args.no_warmup,
        )
        _export_results(results, args.output)
        if args.csv.lower() != "none":
            _export_results_csv(results, args.csv)
    except Exception as exc:
        logger.error("Benchmark failed: %s", exc)
        return 1
    finally:
        reset_redis_client(client=None, pool=None)

    return 0


if __name__ == "__main__":
    sys.exit(main())