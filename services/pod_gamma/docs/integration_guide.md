# Redis Module Integration Guide

## Purpose

This document explains how the Redis module should be integrated with the FastAPI API layer.

The API should never communicate directly with Redis.

Instead, it should interact only with the LeaderboardService.

---

# Architecture

```
                FastAPI API

                     │

                     ▼

          LeaderboardService

                     │

                     ▼

            Redis Connection Pool

                     │

                     ▼

          Redis Sorted Set (ZSET)
```

---

# Service Initialization

Import the service:

```python
from app.services.leaderboard_service import LeaderboardService
```

Create an instance:

```python
service = LeaderboardService()
```

---

# Available Service Methods

## 1. Set Score

```python
service.set_score(username, score)
```

Creates or updates a player's score.

Redis Command:

```
ZADD
```

---

## 2. Increment Score

```python
service.increment_score(username, increment)
```

Atomically increments the player's score.

Redis Command:

```
ZINCRBY
```

---

## 3. Get Player Rank

```python
score, rank = service.get_rank(username)
```

Returns:

- Current Score
- Current Rank

Redis Commands:

```
ZSCORE
ZREVRANK
```

Uses Redis Pipeline for optimized performance.

---

## 4. Get Top Players

```python
players, total = service.get_top_players(limit)
```

Returns:

- Ranked player list
- Total number of players

Redis Command:

```
ZREVRANGE
```

---

## 5. Bulk Insert

```python
service.set_scores_bulk(
    {
        "alice": 1200,
        "bob": 950,
        "charlie": 1700,
    }
)
```

This method inserts or updates multiple players using a single Redis command.

Recommended for:

- Tournament imports
- Initial leaderboard population
- Large datasets

---

## 6. Delete One User

```python
service.delete_user(username)
```

Redis Command:

```
ZREM
```

---

## 7. Batch Delete

```python
service.delete_users(
    [
        "alice",
        "bob",
        "charlie",
    ]
)
```

Uses Redis Pipeline to minimize network overhead.

---

## 8. Reset Leaderboard

```python
service.reset_leaderboard()
```

Removes the complete leaderboard.

Redis Command:

```
DEL
```

---

# Validation

The Redis module already validates:

- Username
- Score
- Increment values

The API layer does not need to repeat these validations unless additional business rules are required.

---

# Exceptions

The following exceptions may be raised by the service:

- UserNotFoundError
- InvalidScoreError
- NegativeScoreError
- RedisUnavailableError
- RedisTimeoutError

The API layer should catch these exceptions and convert them into appropriate HTTP responses.

---

# Thread Safety

The Redis client uses a shared singleton connection pool.

No additional synchronization is required by the API layer.

---

# Performance Features

The Redis module includes:

- Connection Pooling
- Redis Pipeline
- Bulk Insert Operations
- Batch Delete Operations
- Performance Logging
- Benchmark Suite

---

# Environment Variables

Ensure the following variables are configured before running the application:

```
REDIS_HOST
REDIS_PORT
REDIS_DB
REDIS_PASSWORD
REDIS_LEADERBOARD_KEY
```

---

# Integration Checklist

- [ ] Configure `.env`
- [ ] Start Redis server
- [ ] Initialize Redis client
- [ ] Inject `LeaderboardService`
- [ ] Handle service exceptions
- [ ] Run unit tests
- [ ] Verify benchmark results

---

# Notes for Developers

The Redis module is intentionally isolated from the API layer.

Any new leaderboard functionality should be implemented inside `LeaderboardService` rather than directly using Redis commands in the API.

This design improves maintainability, testability, and separation of concerns while allowing future changes to the storage layer without affecting API endpoints.