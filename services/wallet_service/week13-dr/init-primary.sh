#!/bin/bash
set -e

if [ -z "${REPLICATION_PASSWORD:-}" ]; then
    echo "REPLICATION_PASSWORD is required."
    exit 1
fi

psql \
    -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set=replication_password="$REPLICATION_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE wallet_replicator WITH REPLICATION LOGIN PASSWORD %L',
    :'replication_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = 'wallet_replicator'
)
\gexec
SQL

echo "host replication wallet_replicator 0.0.0.0/0 scram-sha-256" \
    >> "$PGDATA/pg_hba.conf"
