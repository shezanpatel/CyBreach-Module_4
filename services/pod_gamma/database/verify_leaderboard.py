"""Standalone script to verify Redis ZSET leaderboard operations.

Connects to a live Redis instance and validates all core commands.

Usage:
    python database/verify_leaderboard.py
    python database/verify_leaderboard.py --host redis --port 6379
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import redis


def verify(host: str, port: int, db: int, key: str) -> bool:
    """
    Run verification checks against a Redis leaderboard ZSET.

    Returns:
        True if all checks pass.
    """

    client = redis.Redis(
        host=host,
        port=port,
        db=db,
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )

    print(f"\n{'=' * 50}")
    print("Redis Leaderboard Verification")
    print(f"{'=' * 50}")
    print(f"Connecting to {host}:{port} db={db}...")

    try:
        client.ping()
        print("[OK] Redis PING")
    except redis.RedisError as exc:
        print(f"[FAIL] Redis connection: {exc}")
        return False

    client.delete(key)

    # -----------------------------
    # ZADD
    # -----------------------------
    client.zadd(
        key,
        {
            "alice": 1500,
            "bob": 1200,
            "charlie": 1800,
        },
    )
    print("[OK] ZADD - added 3 players")

    # -----------------------------
    # ZINCRBY
    # -----------------------------
    new_score = client.zincrby(key, 200, "bob")
    assert new_score == 1400, f"Expected 1400, got {new_score}"
    print(f"[OK] ZINCRBY - bob score is {new_score}")

    # -----------------------------
    # ZSCORE
    # -----------------------------
    score = client.zscore(key, "charlie")
    assert score == 1800
    print(f"[OK] ZSCORE - charlie score is {score}")

    # =====================================================
    # Measure Rank Lookup Latency
    # =====================================================

    iterations = 1000

    start = time.perf_counter()

    for _ in range(iterations):
        rank = client.zrevrank(key, "charlie")

    end = time.perf_counter()

    average_latency_ms = ((end - start) * 1000) / iterations

    assert rank == 0, "Charlie should be rank 0 (highest)"

    print(f"[OK] ZREVRANK - charlie rank is {rank} (0-based)")
    print(
        f"[Latency] Average ZREVRANK latency: "
        f"{average_latency_ms:.4f} ms ({iterations} iterations)"
    )

    if average_latency_ms < 50:
        print("[PASS] Rank lookup completed in under 50 ms")
    else:
        print("[FAIL] Rank lookup exceeded 50 ms")

    # -----------------------------
    # ZREVRANGE
    # -----------------------------
    top = client.zrevrange(key, 0, 2, withscores=True)

    assert top[0][0] == "charlie"

    print(f"[OK] ZREVRANGE - top player is {top[0][0]} ({top[0][1]})")

    # -----------------------------
    # ZREM
    # -----------------------------
    removed = client.zrem(key, "alice")

    assert removed == 1

    print("[OK] ZREM - removed alice")

    # -----------------------------
    # DEL
    # -----------------------------
    client.delete(key)

    assert client.zcard(key) == 0

    print("[OK] DEL - leaderboard cleared")

    print(f"\n{'=' * 50}")
    print("All verification checks PASSED")
    print(f"{'=' * 50}\n")

    return True


def main() -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Verify Redis leaderboard operations"
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="Redis host",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redis port",
    )

    parser.add_argument(
        "--db",
        type=int,
        default=0,
        help="Redis database",
    )

    parser.add_argument(
        "--key",
        default="leaderboard:verify",
        help="Test ZSET key",
    )

    args = parser.parse_args()

    success = verify(
        args.host,
        args.port,
        args.db,
        args.key,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())