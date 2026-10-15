from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


# ============================================================
# DATABASE ENGINE
# ============================================================
#
# Wallet financial operations use explicit row-level locking
# with SELECT ... FOR UPDATE.
#
# READ COMMITTED allows concurrent transactions to wait for
# the wallet row lock instead of generating SERIALIZABLE
# serialization failures under normal wallet contention.
#
# SQLAlchemy SQL echo is disabled so database logging does
# not distort load-test performance measurements.
#
# The connection pool is sized for concurrent Week 11
# load testing while keeping PostgreSQL connection usage
# bounded.
#
# With two Uvicorn workers:
#
#   pool_size=15
#   max_overflow=10
#
# gives a theoretical maximum of 25 connections per worker,
# or 50 application connections across both workers.
#
# ============================================================

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    isolation_level="READ COMMITTED",
    pool_pre_ping=True,
    pool_size=15,
    max_overflow=10,
    pool_timeout=30,
)


# ============================================================
# SESSION FACTORY
# ============================================================
#
# expire_on_commit=False is intentional.
#
# Wallet operations frequently need already-known ORM values
# after a successful financial commit, for example:
#
#   - the committed wallet balance returned to the API
#   - the ledger reference ID included in an event
#
# SQLAlchemy's default expire_on_commit=True expires ORM state
# after every commit. Reading those attributes afterwards can
# issue implicit SELECT statements and automatically begin a
# new transaction.
#
# Under Week 11 high concurrency those post-commit refresh
# transactions can keep database connections checked out until
# request cleanup and exhaust the per-worker connection pools.
#
# Keeping committed ORM state available avoids those unnecessary
# post-commit refresh queries. This does not change the explicit
# transaction boundaries, row-level locks, commits, rollbacks,
# idempotency guarantees, or append-only ledger rules.
#
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


# ============================================================
# SQLALCHEMY BASE
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    """
    Create one SQLAlchemy session for a request.

    Wallet financial operations explicitly control their
    transaction boundaries using db.commit() and db.rollback().

    SQLAlchemy read operations, explicit db.refresh(), and other
    ORM queries may still automatically begin a transaction.

    Under high concurrency, an implicitly opened transaction
    must not remain active when request processing finishes.

    Therefore, before returning the connection to SQLAlchemy's
    connection pool, any still-active transaction is rolled
    back and the session is closed.

    A rollback here does NOT undo a financial transaction that
    has already been successfully committed. It only terminates
    a transaction that remains active at request cleanup.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        try:
            if db.in_transaction():
                db.rollback()

        finally:
            db.close()