# Week 11 Velocity Audit — Pod Alpha Wallet Service

## CyBreach Arena — Module 4

**Pod:** Alpha  
**Component:** Wallet Service  
**Week:** 11  
**Audit:** Performance, Resilience, Disaster Recovery and Velocity Review

---

## 1. Week 11 Objective

Week 11 required Pod Alpha to:

- conduct a wallet stress test;
- exercise 100,000 operations across 1,000 simulated tenants;
- measure throughput;
- measure request latency;
- measure idempotency-collision behaviour;
- identify operations exceeding the 200 ms latency budget;
- optimise identified bottlenecks;
- implement a Wallet Service disaster-recovery runbook;
- test PostgreSQL point-in-time recovery;
- verify that committed data can be recovered after a failure scenario.

The Week 11 Velocity Audit also requires the wallet stress-test status to
be reported and, where the requirement is not fully satisfied, a recovery
plan with concrete scope and next actions.

---

## 2. Functional Baseline

Before performance testing, the Wallet Service already supported the
required wallet functionality from previous implementation weeks,
including:

- wallet credit/debit operations;
- idempotent transaction handling;
- append-only wallet ledger;
- wallet reconciliation;
- credit expiry;
- subscription allocations;
- wallet audit history;
- CSV ledger export;
- multi-currency display;
- budget alerts;
- Kafka event publishing.

The application regression suite remained the correctness gate throughout
Week 11.

Final Week 11 regression result:

99 passed  
12 warnings  
0 failed

Result:

PASS

---

## 3. Stress-Test Design

The Week 11 Locust workload was configured with:

TARGET_OPERATIONS = 100000

TENANT_COUNT = 1000

LATENCY_BUDGET_MS = 200

The workload exercised:

- wallet balance reads;
- deposits;
- withdrawals;
- idempotent request replays;
- idempotency collisions.

Tenant assignment was deterministic across 1,000 simulated tenants.

The test treated an intentional same-key/different-payload idempotency
collision returning HTTP 409 as expected behaviour rather than an
application failure.

---

## 4. Initial Performance Bottleneck

The first high-concurrency runs exposed PostgreSQL connection-pool
exhaustion.

The Wallet Service used two Uvicorn workers.

Each worker could use:

pool_size = 15

max_overflow = 10

This allowed up to 25 database connections per worker and approximately
50 application database connections across the two workers.

Under high concurrency, the PostgreSQL connection pool became saturated.

The investigation identified long-lived request-scoped transactions,
including sessions remaining idle in transaction.

This caused:

- connection starvation;
- request queueing;
- approximately 30-second pool waits;
- HTTP 500 responses during saturation;
- extremely high request latency.

---

## 5. Week 11 Optimisations

### 5.1 Request Transaction Cleanup

The database request lifecycle was updated so that active transactions are
rolled back during request cleanup before the SQLAlchemy session closes.

This prevents abandoned request transactions from remaining open.

---

### 5.2 Non-Locking Read Path

A separate repository operation was introduced:

read_wallet_balance()

It performs read-only balance retrieval without acquiring a
SELECT FOR UPDATE row lock.

It is used only for:

- ordinary balance reads;
- completed idempotency replay paths.

Financial mutation paths continue using locking operations.

This preserves wallet correctness while avoiding unnecessary locks on
read-only operations.

---

### 5.3 SQLAlchemy Expiration Behaviour

The SQLAlchemy session configuration was changed to:

expire_on_commit = False

This prevents committed ORM objects from being automatically expired and
then implicitly reloaded immediately after commit.

The change eliminated the major long-lived post-commit transaction
behaviour observed during the original stress tests.

Financial transaction locking and explicit commit behaviour remain
preserved.

---

### 5.4 Kafka Request-Path Handling

Kafka producer integration was improved to reuse the application's
producer event loop instead of repeatedly creating independent event-loop
execution paths.

This reduced event-publishing overhead while retaining synchronous
confirmation for wallet events.

---

### 5.5 Two Uvicorn Workers

The Wallet Service runs with:

uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

This provides limited process-level request concurrency while retaining
the existing Wallet Service architecture.

---

## 6. Performance Results

### 6.1 20-User Validation

Completed operations:

15,646

HTTP failures:

0

Average latency:

12 ms

Maximum latency:

179 ms

Throughput:

523.67 requests/second

Operations above 200 ms:

0

Result:

PASS against the 200 ms latency budget for this workload.

---

### 6.2 100-User Validation

Completed operations:

17,717

HTTP failures:

0

Average latency:

139 ms

Maximum latency:

468 ms

Throughput:

592.84 requests/second

Operations above 200 ms:

2,627

Over-budget rate:

14.8276%

Database observation:

No transactions remained idle in transaction for more than one second
during the diagnostic snapshot.

Result:

Connection-health improvement confirmed.

Latency requirement not fully satisfied.

---

### 6.3 500-User Validation

Completed operations:

2,197

HTTP failures:

0

Average latency:

435 ms

Maximum latency:

1,244 ms

Throughput:

452.60 requests/second

Operations above 200 ms:

1,742

Over-budget rate:

79.2899%

All 500 simulated users were spawned.

Result:

Service remained operational without HTTP failures during the diagnostic
run, but the 200 ms latency budget was not satisfied.

---

### 6.4 1,000-User Stress Run

The official high-concurrency run was started with:

1,000 simulated users

100 users/second spawn rate

100,000-operation target

10-minute maximum duration

All 1,000 simulated users were successfully spawned.

The service initially processed requests without failures but degraded
under sustained high concurrency.

Observed symptoms included:

- rapidly increasing latency;
- approximately 30-second request delays;
- later HTTP failures;
- latency eventually extending into tens of seconds.

The run therefore did not demonstrate compliance with the required
200 ms latency budget at 1,000-user concurrency.

Result:

STRESS TEST EXECUTED

PERFORMANCE ACCEPTANCE CRITERION NOT PASSED

No claim is made that the 1,000-user workload satisfies the 200 ms
latency requirement.

---

## 7. Idempotency Validation

The stress workload included two separate idempotency scenarios.

### Replay

The same idempotency key and same request payload were replayed.

Expected behaviour:

The previously completed operation is returned without creating another
financial mutation.

### Collision

The same idempotency key was submitted with a different payload.

Expected behaviour:

HTTP 409 conflict.

The load-test harness treated this expected 409 response as successful
collision detection.

The tests confirmed that idempotency protection remained active during
load testing.

---

## 8. Disaster-Recovery Validation

PostgreSQL WAL archiving was enabled with:

archive_mode = on

wal_level = replica

archive_timeout = 60s

Archived WAL segments were successfully written to a dedicated persistent
archive volume.

A physical PostgreSQL base backup was then created using pg_basebackup.

---

## 9. Point-in-Time Recovery Test

An isolated PostgreSQL recovery instance was created from:

- the physical base backup;
- archived WAL segments.

Recovery target:

2026-09-26 14:57:22.979626+00

A test transaction committed before the recovery target:

BEFORE_RECOVERY_TARGET_20260926

Timestamp:

2026-09-26 14:57:17.941876+00

A second transaction committed after the recovery target:

AFTER_RECOVERY_TARGET_20260926

Timestamp:

2026-09-26 14:57:36.482746+00

After PITR, the recovered database contained:

BEFORE_RECOVERY_TARGET_20260926

and did not contain:

AFTER_RECOVERY_TARGET_20260926

The live database continued to contain both transactions.

The recovery instance successfully promoted after reaching the configured
target.

Result:

PASS

This demonstrated that the Wallet Service PostgreSQL database can be
restored to a selected point in time while preserving transactions that
were committed before the recovery target.

---

## 10. Disaster-Recovery Runbook

The validated recovery procedure is documented in:

docs/disaster_recovery_runbook.md

The runbook covers:

- WAL archive verification;
- WAL archive permissions;
- physical base backup;
- recovery preparation;
- recovery target configuration;
- isolated PostgreSQL recovery;
- promotion;
- validation;
- safety controls.

Result:

PASS

---

## 11. Week 11 Velocity Audit Status

### Functional Regression

PASS

99 tests passed.

### WAL Archiving

PASS

### Physical Base Backup

PASS

### PostgreSQL PITR

PASS

### Live Database Preservation During Recovery Drill

PASS

### Idempotency Behaviour

PASS

### Low-Concurrency Latency Validation

PASS

### 1,000-Tenant Stress-Test Execution

EXECUTED

### 200 ms High-Concurrency Latency Requirement

NOT YET PASSED

---

## 12. Performance Recovery Plan

The remaining Week 11 gap is high-concurrency wallet performance.

The current implementation preserves financial correctness, transaction
locking, idempotency, audit history and synchronous event-delivery
semantics.

Further optimisation must not weaken those guarantees merely to improve
benchmark results.

### Priority 1 — Database Request Profiling

Measure per-endpoint SQL execution time and connection-acquisition time
under controlled load.

Identify whether high-concurrency latency is dominated by:

- connection acquisition;
- row-lock contention;
- transaction duration;
- budget-alert queries;
- database commits;
- idempotency lookups;
- synchronous Kafka publication.

---

### Priority 2 — Mutation Transaction Reduction

Review deposit and withdrawal request paths for database work occurring
after the core financial transaction commits.

Separate non-critical post-transaction processing where this can be done
without weakening financial correctness or event guarantees.

---

### Priority 3 — Budget Alert Cost

Budget-alert evaluation currently participates in balance-changing
request processing.

Profile its:

- database lookup cost;
- locking behaviour;
- commit behaviour;
- notification publishing cost.

Optimisation must preserve Week 10 budget-alert behaviour.

---

### Priority 4 — Kafka Latency

Measure Kafka publication latency independently from database latency.

Determine how much synchronous event acknowledgement contributes to the
end-to-end request latency.

Any future asynchronous design requires an explicit reliability mechanism
such as a transactional outbox before synchronous guarantees are removed.

---

### Priority 5 — Database Capacity

Evaluate database connection capacity against application worker
concurrency.

Do not simply increase connection counts without measurement because
excessive PostgreSQL connections can reduce overall performance.

---

### Priority 6 — Controlled Retesting

Performance changes should be validated progressively:

20 users

100 users

500 users

1,000 users

The 100,000-operation stress test should only be repeated after the
identified high-concurrency bottleneck has been materially changed.

This avoids repeatedly executing the same known failing workload.

---

## 13. Scope Protection

The following behaviour must not be removed merely to make the benchmark
pass:

- financial row locking;
- idempotency enforcement;
- append-only ledger integrity;
- reconciliation;
- credit expiry;
- audit history;
- subscription allocations;
- budget alerts;
- required wallet events;
- disaster-recovery capability.

Correctness and auditability remain mandatory requirements for the wallet
system.

---

## 14. Recovery-Plan Decision

Week 11 produced a working and regression-tested Wallet Service with
validated PostgreSQL disaster recovery.

The high-concurrency latency target remains an open performance item.

Rather than repeatedly rerunning an unchanged stress workload, the
project will preserve the measured Week 11 evidence and continue using the
documented recovery plan.

Future performance work will focus on measured database and request-path
bottlenecks before another full 1,000-user / 100,000-operation validation
run.

---

## 15. Final Week 11 Status

Functional wallet behaviour:

PASS

Regression suite:

PASS — 99 tests

Idempotency:

PASS

WAL archiving:

PASS

Physical backup:

PASS

Point-in-time recovery:

PASS

Disaster-recovery runbook:

PASS

1,000-user stress test:

EXECUTED

High-concurrency 200 ms latency criterion:

OPEN — PERFORMANCE RECOVERY PLAN REQUIRED

Week 11 is therefore documented with the high-concurrency performance gap
explicitly recorded rather than incorrectly reporting the stress test as
passing.
