# Wallet Service PostgreSQL Disaster Recovery Runbook

## CyBreach Arena — Module 4 — Pod Alpha

**Component:** Wallet Service  
**Database:** PostgreSQL 16  
**Recovery Method:** Write-Ahead Log Archiving + Point-in-Time Recovery (PITR)  
**Validation:** Week 11 Disaster-Recovery Drill

---

## 1. Purpose

This runbook defines the disaster-recovery procedure for the CyBreach
Module 4 Wallet Service PostgreSQL database.

The objective is to ensure that wallet and ledger data can be recovered
to a known point in time after database corruption, operator error, or
another database failure scenario.

The recovery strategy uses:

- PostgreSQL physical base backups
- Write-Ahead Log (WAL) archiving
- Point-in-Time Recovery (PITR)
- Isolated recovery validation
- Recovery-target promotion

The production/live database must not be overwritten during a recovery
test.

---

## 2. Current PostgreSQL Configuration

PostgreSQL version:

PostgreSQL 16

Database:

wallet_db

Database user:

wallet_user

Primary PostgreSQL data directory:

/var/lib/postgresql/data

WAL archive directory:

/var/lib/postgresql/wal_archive

Required PostgreSQL configuration:

wal_level = replica
archive_mode = on
archive_timeout = 60s

Archive command:

test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f

The WAL archive is stored in a dedicated persistent Docker volume:

postgres_wal_archive

The primary database is stored separately in:

postgres_data

---

## 3. Verify WAL Archiving

Check configuration:

docker compose exec postgres psql \
-U wallet_user \
-d wallet_db \
-c "SHOW archive_mode;"

docker compose exec postgres psql \
-U wallet_user \
-d wallet_db \
-c "SHOW archive_command;"

docker compose exec postgres psql \
-U wallet_user \
-d wallet_db \
-c "SHOW wal_level;"

Expected:

archive_mode = on
wal_level = replica

Check archiver status:

docker compose exec postgres psql \
-U wallet_user \
-d wallet_db \
-c "SELECT archived_count,
           failed_count,
           last_archived_wal,
           last_archived_time,
           last_failed_wal
    FROM pg_stat_archiver;"

Force a WAL switch when validating archival:

docker compose exec postgres psql \
-U wallet_user \
-d wallet_db \
-c "SELECT pg_switch_wal();"

Verify archived WAL:

docker compose exec postgres \
sh -c 'ls -lah /var/lib/postgresql/wal_archive'

---

## 4. WAL Archive Permissions

The WAL archive directory must be writable by the PostgreSQL operating
system user.

Correct ownership:

postgres:postgres

Correct permissions:

700

Repair commands:

docker compose exec -u root postgres \
chown -R postgres:postgres /var/lib/postgresql/wal_archive

docker compose exec -u root postgres \
chmod 700 /var/lib/postgresql/wal_archive

---

## 5. Create a Physical Base Backup

Create a temporary base backup inside the PostgreSQL container:

docker compose exec postgres \
pg_basebackup \
-U wallet_user \
-D /tmp/week11-basebackup \
-F tar \
-z \
-X stream \
-P

Copy the backup outside the database container:

mkdir -p week11-dr/basebackup

docker cp \
wallet-postgres:/tmp/week11-basebackup/. \
./week11-dr/basebackup/

Expected backup artifacts include:

- base.tar.gz
- pg_wal.tar.gz
- backup_manifest

Base backups must be stored separately from the active PostgreSQL data
directory.

---

## 6. Recovery Procedure

Create an isolated recovery directory:

rm -rf week11-dr/recovery-data
mkdir -p week11-dr/recovery-data

Extract the base backup:

tar -xzf week11-dr/basebackup/base.tar.gz \
-C week11-dr/recovery-data

Extract the backup WAL:

tar -xzf week11-dr/basebackup/pg_wal.tar.gz \
-C week11-dr/recovery-data/pg_wal

Copy archived WAL files from the primary database:

rm -rf week11-dr/wal-archive
mkdir -p week11-dr/wal-archive

docker cp \
wallet-postgres:/var/lib/postgresql/wal_archive/. \
./week11-dr/wal-archive/

---

## 7. Configure Point-in-Time Recovery

Add the required recovery settings to:

week11-dr/recovery-data/postgresql.auto.conf

Required settings:

restore_command = 'cp /wal_archive/%f %p'
recovery_target_time = '<UTC RECOVERY TARGET>'
recovery_target_action = 'promote'

Create the PostgreSQL recovery signal:

touch week11-dr/recovery-data/recovery.signal

Set data-directory permissions:

chmod 700 week11-dr/recovery-data

---

## 8. Start an Isolated Recovery Instance

The recovery database must use a different container and host port so
that the live Wallet Service database remains untouched.

Example:

docker run -d \
--name wallet-postgres-recovery \
-p 55432:5432 \
-v "$PWD/week11-dr/recovery-data:/var/lib/postgresql/data" \
-v "$PWD/week11-dr/wal-archive:/wal_archive:ro" \
postgres:16

Inspect recovery logs:

docker logs wallet-postgres-recovery --tail=100

Verify recovery status:

docker exec wallet-postgres-recovery psql \
-U wallet_user \
-d wallet_db \
-c "SELECT pg_is_in_recovery();"

After recovery_target_action=promote completes successfully:

pg_is_in_recovery() = false

---

## 9. Week 11 Recovery Drill Evidence

Recovery drill date:

2026-09-26

Configured recovery target:

2026-09-26 14:57:22.979626+00

Test transaction before recovery target:

BEFORE_RECOVERY_TARGET_20260926

Transaction timestamp:

2026-09-26 14:57:17.941876+00

Test transaction after recovery target:

AFTER_RECOVERY_TARGET_20260926

Transaction timestamp:

2026-09-26 14:57:36.482746+00

PostgreSQL recovery reported:

starting point-in-time recovery to
2026-09-26 14:57:22.979626+00

Recovery stopped before the later transaction committed.

Recovered database result:

BEFORE_RECOVERY_TARGET_20260926 = PRESENT
AFTER_RECOVERY_TARGET_20260926 = ABSENT

Live database result:

BEFORE_RECOVERY_TARGET_20260926 = PRESENT
AFTER_RECOVERY_TARGET_20260926 = PRESENT

The isolated recovery database was successfully promoted after reaching
the requested recovery target.

Result:

PASS

The test demonstrates that PostgreSQL WAL archiving and PITR can restore
the Wallet Service database to a selected point in time without
modifying the live database.

---

## 10. Recovery Validation Checklist

Before declaring recovery complete:

1. Confirm PostgreSQL starts successfully.
2. Confirm WAL restoration completes without unrecoverable errors.
3. Confirm the requested recovery target was reached.
4. Confirm pg_is_in_recovery() becomes false after promotion.
5. Verify expected wallet balances.
6. Verify wallet ledger entries.
7. Verify ledger append-only integrity.
8. Verify idempotency records.
9. Verify subscription allocations.
10. Verify wallet audit history.
11. Run Wallet Service automated regression tests.
12. Re-enable application traffic only after validation succeeds.

---

## 11. Safety Rules

Never run:

docker compose down -v

during normal recovery work because it may delete persistent Docker
volumes.

Never overwrite the active PostgreSQL data directory during a recovery
drill.

Always recover into an isolated database instance first.

Never delete WAL archives required by the latest valid base backup.

Never declare a recovery successful until wallet balances and ledger
history have been validated.

---

## 12. Week 11 Result

WAL archiving: PASS

Physical base backup: PASS

Point-in-time recovery: PASS

Recovery target enforcement: PASS

Isolated recovery: PASS

Live database preserved: PASS

Disaster-recovery procedure: VALIDATED
