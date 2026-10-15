# Redis Module Documentation

## Overview

The Redis module is responsible for managing all leaderboard-related data and operations using Redis Sorted Sets (ZSET). It provides a clean service layer for interacting with Redis while hiding connection management and low-level Redis commands from the API layer.

The module is designed to be:

- Secure
- Reusable
- High Performance
- Easy to Integrate
- Production Ready

---

# Module Structure

```
app/
├── db/
│   └── redis_client.py
│
├── services/
│   └── leaderboard_service.py
│
└── utils/
    └── benchmark.py
```

---

# Responsibilities

## Redis Connection Management

Implemented in:

```
app/db/redis_client.py
```

Features:

- Singleton Redis Client
- Connection Pooling
- Redis Authentication
- Connection Retry
- Health Checks
- Redis Metrics
- Graceful Shutdown
- Structured Logging

---

## Leaderboard Service

Implemented in:

```
app/services/leaderboard_service.py
```

Provides all leaderboard operations while abstracting Redis implementation details.

### Available Methods

| Method | Description |
|---------|-------------|
| set_score() | Create or update player score |
| increment_score() | Atomically increase player score |
| get_rank() | Retrieve player rank and score |
| get_top_players() | Fetch top ranked players |
| delete_user() | Remove a player |
| delete_users() | Remove multiple players |
| set_scores_bulk() | Insert/update multiple players |
| reset_leaderboard() | Clear leaderboard |

---

# Redis Commands Used

| Service Method | Redis Command |
|---------------|---------------|
| set_score() | ZADD |
| increment_score() | ZINCRBY |
| get_rank() | ZSCORE + ZREVRANK |
| get_top_players() | ZREVRANGE |
| delete_user() | ZREM |
| delete_users() | Pipeline + ZREM |
| reset_leaderboard() | DEL |

---

# Performance Optimizations

The module includes several Redis optimizations:

## Connection Pool

A shared Redis connection pool is used to minimize connection overhead and improve scalability.

---

## Redis Pipeline

Rank lookups use Redis Pipeline to reduce multiple network round trips into a single request.

---

## Bulk Insert

Multiple player scores can be inserted using one ZADD command instead of repeated individual inserts.

---

## Batch Delete

Multiple users are removed using Redis Pipeline for improved performance.

---

## Input Validation

Validation is performed before any Redis operation.

Validated fields include:

- Username
- Score
- Increment value

Invalid requests are rejected before reaching Redis.

---

# Benchmark Utility

Benchmark implementation:

```
app/utils/benchmark.py
```

Benchmarked operations include:

- Single Insert
- Bulk Insert
- Increment
- Rank Lookup
- Top Player Retrieval
- Batch Delete

Performance metrics:

- Average Latency
- Throughput
- Minimum Latency
- Maximum Latency
- P95 Latency
- P99 Latency

Benchmark reports can be exported as:

- JSON
- CSV

---

# Error Handling

The Redis module raises custom exceptions:

- UserNotFoundError
- InvalidScoreError
- NegativeScoreError
- RedisUnavailableError
- RedisTimeoutError

The API layer should convert these exceptions into HTTP responses.

---

# Thread Safety

The Redis client uses a singleton connection pool and is safe for concurrent access.

---

# Future Enhancements

Possible future improvements:

- Leaderboard caching
- Redis Cluster support
- Redis Sentinel support
- Leaderboard pagination
- Seasonal leaderboards
- Multiple leaderboard namespaces