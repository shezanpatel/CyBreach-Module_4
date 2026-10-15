from decimal import Decimal
import uuid

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.wallet_balance import WalletBalance
from app.services.wallet_service import deposit_money


TENANT_COUNT = 1000
USERS_PER_TENANT = 1
INITIAL_BALANCE = Decimal("1000.00")
CURRENCY = "USD"


def seed_wallets() -> None:
    db = SessionLocal()

    created = 0
    skipped = 0

    try:
        for tenant_number in range(1, TENANT_COUNT + 1):
            for user_number in range(1, USERS_PER_TENANT + 1):
                user_id = (
                    f"load-tenant-{tenant_number}-user-{user_number}"
                )

                existing_wallet = db.execute(
                    select(WalletBalance).where(
                        WalletBalance.user_id == user_id,
                        WalletBalance.currency == CURRENCY,
                    )
                ).scalar_one_or_none()

                if existing_wallet is not None:
                    skipped += 1
                    continue

                deposit_money(
                    db=db,
                    user_id=user_id,
                    amount=INITIAL_BALANCE,
                    currency=CURRENCY,
                    idempotency_key=f"seed-{uuid.uuid4()}",
                )

                created += 1

                if created % 100 == 0:
                    print(
                        f"Seeded {created}/{TENANT_COUNT} wallets"
                    )

        print()
        print("Load-test wallet seeding completed.")
        print(f"Created: {created}")
        print(f"Skipped: {skipped}")
        print(f"Total tenants: {TENANT_COUNT}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_wallets()