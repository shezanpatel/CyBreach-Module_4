from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.database import SessionLocal
from app.main import app
from app.models.wallet_ledger import WalletLedger
from app.models.wallet_ledger_entry import WalletLedgerEntry
from app.repositories.wallet_repository import create_ledger_entry


client = TestClient(app)


def test_wallet_audit_history_pagination_with_10000_plus_entries():
    """
    Week 9 requirement:
    verify audit-history pagination with more than 10,000
    valid double-entry ledger entries.
    """

    db = SessionLocal()
    user_id = f"audit_10k_{uuid4().hex}"

    try:
        for index in range(5001):
            ledger = WalletLedger(
                id=uuid4(),
                user_id=user_id,
                transaction_type="CREDIT",
                currency="USD",
                amount=Decimal("1.00"),
                reference_id=f"audit-ref-{index}-{uuid4().hex}",
                module_source="mod4",
            )

            create_ledger_entry(
                db=db,
                ledger=ledger,
            )

            if (index + 1) % 500 == 0:
                db.commit()

        db.commit()

    finally:
        db.close()

    response = client.get(
        f"/wallet/history/{user_id}",
        params={
            "module_source": "mod4",
            "limit": 1000,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    first_page = response.json()

    assert first_page["user_id"] == user_id
    assert first_page["total"] == 10002
    assert first_page["limit"] == 1000
    assert first_page["offset"] == 0
    assert len(first_page["entries"]) == 1000

    response = client.get(
        f"/wallet/history/{user_id}",
        params={
            "module_source": "mod4",
            "limit": 1000,
            "offset": 10000,
        },
    )

    assert response.status_code == 200

    final_page = response.json()

    assert final_page["total"] == 10002
    assert final_page["limit"] == 1000
    assert final_page["offset"] == 10000
    assert len(final_page["entries"]) == 2


def test_wallet_ledger_entry_is_append_only():
    """
    Week 9 requirement:
    PostgreSQL must reject UPDATE and DELETE against
    wallet_ledger_entries.
    """

    db = SessionLocal()
    user_id = f"append_only_{uuid4().hex}"

    try:
        ledger = WalletLedger(
            id=uuid4(),
            user_id=user_id,
            transaction_type="CREDIT",
            currency="USD",
            amount=Decimal("1.00"),
            reference_id=f"append-only-{uuid4().hex}",
            module_source="mod4",
        )

        create_ledger_entry(
            db=db,
            ledger=ledger,
        )

        db.commit()

        entry = (
            db.query(WalletLedgerEntry)
            .filter(
                WalletLedgerEntry.transaction_id
                == ledger.id
            )
            .filter(
                WalletLedgerEntry.entry_type
                == "CREDIT"
            )
            .one()
        )

        entry_id = entry.id

        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    """
                    UPDATE wallet_ledger_entries
                    SET amount = 999
                    WHERE id = :entry_id
                    """
                ),
                {"entry_id": entry_id},
            )
            db.commit()

        db.rollback()

        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    """
                    DELETE FROM wallet_ledger_entries
                    WHERE id = :entry_id
                    """
                ),
                {"entry_id": entry_id},
            )
            db.commit()

        db.rollback()

        stored_entry = (
            db.query(WalletLedgerEntry)
            .filter(
                WalletLedgerEntry.id == entry_id
            )
            .one()
        )

        assert stored_entry.amount == Decimal("1.00")

    finally:
        db.close()
