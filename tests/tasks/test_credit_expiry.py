 
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.wallet_balance import WalletBalance
from app.models.wallet_credit import WalletCredit
from app.models.wallet_ledger import WalletLedger
from app.tasks.credit_expiry import expire_wallet_credits


# ============================================================
# UNIT TEST
# ============================================================


@patch("app.tasks.credit_expiry.update_wallet_credit")
@patch("app.tasks.credit_expiry.create_ledger_entry")
@patch("app.tasks.credit_expiry.update_wallet_balance")
@patch("app.tasks.credit_expiry.get_wallet_balance")
@patch("app.tasks.credit_expiry.get_expired_wallet_credits")
def test_expire_wallet_credits(
    mock_get_expired_credits,
    mock_get_wallet_balance,
    mock_update_wallet_balance,
    mock_create_ledger_entry,
    mock_update_wallet_credit,
):
    db = MagicMock()

    credit = WalletCredit(
        id=uuid4(),
        user_id="expiry_test_user",
        currency="USD",
        amount=Decimal("100.00"),
        remaining_amount=Decimal("100.00"),
        reference_id="credit-ref-001",
        created_at=datetime.now(timezone.utc) - timedelta(days=91),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    balance = WalletBalance(
        user_id="expiry_test_user",
        currency="USD",
        available_balance=Decimal("500.00"),
    )

    mock_get_expired_credits.return_value = [credit]
    mock_get_wallet_balance.return_value = balance

    result = expire_wallet_credits(db)

    # ---------------------------------------------------------
    # Verify wallet balance
    # ---------------------------------------------------------
    assert balance.available_balance == Decimal("400.00")

    # ---------------------------------------------------------
    # Verify credit was completely consumed
    # ---------------------------------------------------------
    assert credit.remaining_amount == Decimal("0.00")

    # ---------------------------------------------------------
    # Verify expiration timestamp
    # ---------------------------------------------------------
    assert credit.expired_at is not None

    # ---------------------------------------------------------
    # Verify ledger entry
    # ---------------------------------------------------------
    mock_create_ledger_entry.assert_called_once()

    ledger = mock_create_ledger_entry.call_args.kwargs["ledger"]

    assert ledger.user_id == "expiry_test_user"
    assert ledger.currency == "USD"
    assert ledger.transaction_type == "CREDIT_EXPIRY"
    assert ledger.amount == Decimal("100.00")
    assert ledger.reference_id == str(credit.id)

    # ---------------------------------------------------------
    # Verify credit update
    # ---------------------------------------------------------
    mock_update_wallet_credit.assert_called_once()

    # ---------------------------------------------------------
    # Verify result
    # ---------------------------------------------------------
    assert result["processed_count"] == 1
    assert result["skipped_count"] == 0
    assert result["processed"][0]["status"] == "EXPIRED"


@patch("app.tasks.credit_expiry.get_expired_wallet_credits")
def test_expire_wallet_credits_no_expired_credits(
    mock_get_expired_credits,
):
    db = MagicMock()

    mock_get_expired_credits.return_value = []

    result = expire_wallet_credits(db)

    assert result["processed_count"] == 0
    assert result["skipped_count"] == 0
    assert result["processed"] == []
    assert result["skipped"] == []


# ============================================================
# DATABASE / INTEGRATION TEST
# ============================================================


def test_credit_expiry_database_flow():
    db = SessionLocal()

    user_id = f"expiry_db_test_{uuid4().hex[:8]}"
    currency = "USD"

    try:
        # -----------------------------------------------------
        # STEP 1: Create wallet with $500
        # -----------------------------------------------------
        wallet = WalletBalance(
            user_id=user_id,
            currency=currency,
            available_balance=Decimal("500.00"),
        )

        db.add(wallet)
        db.flush()

        # -----------------------------------------------------
        # STEP 2: Create an expired credit of $100
        # -----------------------------------------------------
        now = datetime.now(timezone.utc)

        credit = WalletCredit(
            user_id=user_id,
            currency=currency,
            amount=Decimal("100.00"),
            remaining_amount=Decimal("100.00"),
            reference_id=str(uuid4()),
            created_at=now - timedelta(days=100),
            expires_at=now - timedelta(days=10),
        )

        db.add(credit)
        db.commit()

        # -----------------------------------------------------
        # STEP 3: Run credit expiry
        # -----------------------------------------------------
        result = expire_wallet_credits(db)

        # -----------------------------------------------------
        # STEP 4: Verify processing result
        # -----------------------------------------------------
        assert result["processed_count"] == 1
        assert result["skipped_count"] == 0

        # -----------------------------------------------------
        # STEP 5: Reload wallet
        # -----------------------------------------------------
        db.refresh(wallet)

        assert wallet.available_balance == Decimal("400.00")

        # -----------------------------------------------------
        # STEP 6: Reload credit
        # -----------------------------------------------------
        db.refresh(credit)

        assert credit.remaining_amount == Decimal("0.00")
        assert credit.expired_at is not None

        # -----------------------------------------------------
        # STEP 7: Verify expiry ledger transaction
        # -----------------------------------------------------
        expiry_entry = (
            db.query(WalletLedger)
            .filter(
                WalletLedger.user_id == user_id,
                WalletLedger.transaction_type == "CREDIT_EXPIRY",
                WalletLedger.reference_id == str(credit.id),
            )
            .first()
        )

        assert expiry_entry is not None
        assert expiry_entry.amount == Decimal("100.00")
        assert expiry_entry.currency == currency

        # -----------------------------------------------------
        # STEP 8: Preserve append-only ledger history
        # -----------------------------------------------------
        #
        # Week 9 makes wallet_ledger and wallet_ledger_entries
        # append-only at the database level. The integration test
        # must therefore never delete the financial audit trail.
        #
        # The test uses a unique user_id, so its immutable ledger
        # transaction can safely remain as historical test data.
        # -----------------------------------------------------

        # -----------------------------------------------------
        # STEP 9: Clean up mutable test credit and wallet
        # -----------------------------------------------------
        db.query(WalletCredit).filter(
            WalletCredit.user_id == user_id
        ).delete(
            synchronize_session=False
        )

        db.query(WalletBalance).filter(
            WalletBalance.user_id == user_id
        ).delete(
            synchronize_session=False
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
