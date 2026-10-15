#!/bin/bash
set -e

export PGPASSWORD="$REPLICATION_PASSWORD"

mkdir -p "$PGDATA"
chmod 700 "$PGDATA"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "Waiting for Week 13 primary..."

    until pg_isready \
        -h week13-primary \
        -p 5432 \
        -U wallet_replicator
    do
        sleep 2
    done

    echo "Creating replica from pg_basebackup..."

    rm -rf "${PGDATA:?}"/*

    pg_basebackup \
        -h week13-primary \
        -p 5432 \
        -U wallet_replicator \
        -D "$PGDATA" \
        -Fp \
        -Xs \
        -P \
        -R

    chmod 700 "$PGDATA"

    echo "Replica base backup completed."
fi

chmod 700 "$PGDATA"

exec postgres \
    -c hot_standby=on
