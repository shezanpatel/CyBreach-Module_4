import threading
import time
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.exc import OperationalError

from app.core.database import SessionLocal
from app.models.idempotency_key import IdempotencyKey
from app.repositories.idempotency_repository import (
    claim_idempotency_key,
    generate_request_hash,
)


def _is_serialization_failure(exc):
    """
    PostgreSQL serialization failures use SQLSTATE 40001.
    """

    original = getattr(exc, "orig", None)

    sqlstate = getattr(
        original,
        "sqlstate",
        None,
    )

    if sqlstate is None:
        sqlstate = getattr(
            original,
            "pgcode",
            None,
        )

    if sqlstate is None:
        diag = getattr(
            original,
            "diag",
            None,
        )

        sqlstate = getattr(
            diag,
            "sqlstate",
            None,
        )

    return sqlstate == "40001"


def test_concurrent_same_idempotency_key_has_single_winner():
    key = "concurrent-idempotency-test"

    request_hash = generate_request_hash(
        user_id="concurrent-user",
        endpoint="/wallet/deposit",
        amount=Decimal("50.00"),
        currency="USD",
        reference_id=None,
    )

    barrier = threading.Barrier(2)

    results = []
    errors = []

    lock = threading.Lock()

    def worker():
        max_attempts = 3

        for attempt in range(max_attempts):
            db = SessionLocal()

            try:
                if attempt == 0:
                    barrier.wait()

                record, created = claim_idempotency_key(
                    db=db,
                    key=key,
                    user_id="concurrent-user",
                    endpoint="/wallet/deposit",
                    request_hash=request_hash,
                )

                db.commit()

                with lock:
                    results.append(
                        {
                            "created": created,
                            "key": record.key,
                        }
                    )

                return

            except OperationalError as exc:
                db.rollback()

                if (
                    _is_serialization_failure(exc)
                    and attempt < max_attempts - 1
                ):
                    time.sleep(
                        0.05 * (2 ** attempt)
                    )
                    continue

                with lock:
                    errors.append(exc)

                return

            except Exception as exc:
                db.rollback()

                with lock:
                    errors.append(exc)

                return

            finally:
                db.close()

    threads = [
        threading.Thread(target=worker)
        for _ in range(2)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # ---------------------------------------------------------
    # Both requests must eventually complete.
    # ---------------------------------------------------------

    assert errors == []

    assert len(results) == 2

    # ---------------------------------------------------------
    # Exactly one request may create the key.
    # ---------------------------------------------------------

    created_results = [
        result
        for result in results
        if result["created"] is True
    ]

    existing_results = [
        result
        for result in results
        if result["created"] is False
    ]

    assert len(created_results) == 1
    assert len(existing_results) == 1

    # ---------------------------------------------------------
    # Both requests must reference the same key.
    # ---------------------------------------------------------

    assert all(
        result["key"] == key
        for result in results
    )

    # ---------------------------------------------------------
    # Verify only one database record exists.
    # ---------------------------------------------------------

    db = SessionLocal()

    try:
        records = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.key == key
            )
            .all()
        )

        assert len(records) == 1

        assert (
            records[0].request_hash
            == request_hash
        )

        assert (
            records[0].user_id
            == "concurrent-user"
        )

        assert (
            records[0].endpoint
            == "/wallet/deposit"
        )

    finally:
        db.execute(
            delete(IdempotencyKey).where(
                IdempotencyKey.key == key
            )
        )

        db.commit()
        db.close()