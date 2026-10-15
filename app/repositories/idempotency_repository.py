import hashlib
import json

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKey


def get_idempotency_key(
    db: Session,
    key: str,
):
    """
    Retrieve an idempotency record by its primary key.
    """

    return (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.key == key
        )
        .first()
    )


def create_idempotency_key(
    db: Session,
    record: IdempotencyKey,
):
    """
    Add an idempotency record to the current transaction.

    This function is retained for compatibility with existing
    code. New wallet operations should use claim_idempotency_key()
    so concurrent requests are handled atomically.
    """

    db.add(record)

    return record


def claim_idempotency_key(
    db: Session,
    *,
    key: str,
    user_id: str,
    endpoint: str,
    request_hash: str,
):
    """
    Atomically claim an idempotency key.

    PostgreSQL's primary-key constraint guarantees that two
    concurrent requests cannot both successfully claim the
    same key.

    Returns:

        (record, created)

    where:

        created=True
            This request created the idempotency record.

        created=False
            The key already existed.
    """

    statement = (
        insert(IdempotencyKey)
        .values(
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            request_hash=request_hash,
            response_data="success",
        )
        .on_conflict_do_nothing(
            index_elements=[
                IdempotencyKey.key
            ]
        )
        .returning(IdempotencyKey.key)
    )

    result = db.execute(statement)

    created_key = result.scalar_one_or_none()

    if created_key is not None:
        record = get_idempotency_key(
            db,
            key,
        )

        return record, True

    record = get_idempotency_key(
        db,
        key,
    )

    return record, False


def generate_request_hash(
    *,
    user_id: str,
    endpoint: str,
    amount: str,
    currency: str,
    reference_id: str | None = None,
) -> str:
    """
    Generate a deterministic SHA-256 fingerprint for a
    wallet request.

    The same logical request always produces the same hash.

    Any change to a protected request parameter produces a
    different hash.

    JSON serialization uses sorted keys and compact separators
    so the hash is deterministic.
    """

    payload = {
        "amount": str(amount),
        "currency": currency.upper(),
        "endpoint": endpoint,
        "reference_id": reference_id,
        "user_id": user_id,
    }

    canonical_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_payload.encode("utf-8")
    ).hexdigest()