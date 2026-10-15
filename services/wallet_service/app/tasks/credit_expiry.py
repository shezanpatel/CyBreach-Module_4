from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.wallet_ledger import WalletLedger
from app.repositories.wallet_repository import (
    create_ledger_entry,
    get_expired_wallet_credits,
    get_wallet_balance,
    update_wallet_balance,
    update_wallet_credit,
)


def expire_wallet_credits(
    db: Session,
):
    """
    Expire all wallet credits whose expiration date has passed.

    For every expired credit with a remaining balance:

    1. Lock the expired credit.
    2. Find and lock the user's wallet balance.
    3. Remove the remaining credit amount from the wallet balance.
    4. Create a CREDIT_EXPIRY ledger entry.
    5. Set the credit's remaining amount to zero.
    6. Record the expiration timestamp.
    7. Commit the transaction.

    Returns a summary of the credits processed.
    """

    expired_credits = get_expired_wallet_credits(db)

    processed = []
    skipped = []

    for credit in expired_credits:
        try:
            # -------------------------------------------------
            # STEP 1: Get and lock the user's wallet balance
            # -------------------------------------------------
            balance = get_wallet_balance(
                db=db,
                user_id=credit.user_id,
                currency=credit.currency,
            )

            if balance is None:
                skipped.append(
                    {
                        "credit_id": str(credit.id),
                        "reason": "WALLET_NOT_FOUND",
                    }
                )
                continue

            # -------------------------------------------------
            # STEP 2: Determine amount to expire
            # -------------------------------------------------
            expiry_amount = Decimal(str(credit.remaining_amount))

            if expiry_amount <= Decimal("0.00"):
                skipped.append(
                    {
                        "credit_id": str(credit.id),
                        "reason": "NO_REMAINING_AMOUNT",
                    }
                )
                continue

            # -------------------------------------------------
            # STEP 3: Prevent negative wallet balance
            # -------------------------------------------------
            if balance.available_balance < expiry_amount:
                skipped.append(
                    {
                        "credit_id": str(credit.id),
                        "reason": "INSUFFICIENT_WALLET_BALANCE",
                    }
                )
                continue

            # -------------------------------------------------
            # STEP 4: Remove expired amount from wallet
            # -------------------------------------------------
            balance.available_balance -= expiry_amount

            update_wallet_balance(
                db=db,
                balance=balance,
            )

            # -------------------------------------------------
            # STEP 5: Create expiry ledger entry
            # -------------------------------------------------
            ledger = WalletLedger(
                id=uuid4(),
                user_id=credit.user_id,
                transaction_type="CREDIT_EXPIRY",
                currency=credit.currency,
                amount=expiry_amount,
                reference_id=str(credit.id),
            )

            create_ledger_entry(
                db=db,
                ledger=ledger,
            )

            # -------------------------------------------------
            # STEP 6: Mark credit as expired
            # -------------------------------------------------
            credit.remaining_amount = Decimal("0.00")
            credit.expired_at = datetime.now(timezone.utc)

            update_wallet_credit(
                db=db,
                credit=credit,
            )

            # -------------------------------------------------
            # STEP 7: Commit this credit's transaction
            # -------------------------------------------------
            db.commit()

            processed.append(
                {
                    "credit_id": str(credit.id),
                    "user_id": credit.user_id,
                    "currency": credit.currency,
                    "expired_amount": expiry_amount,
                    "status": "EXPIRED",
                }
            )

        except Exception:
            db.rollback()
            raise

    return {
        "processed": processed,
        "skipped": skipped,
        "processed_count": len(processed),
        "skipped_count": len(skipped),
    }
