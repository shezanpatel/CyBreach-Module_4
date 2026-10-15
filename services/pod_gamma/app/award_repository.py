from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.award_models import BadgeAwardDB


async def find_award(
    session: AsyncSession,
    badge_id: str,
    tenant_id: str,
) -> BadgeAwardDB | None:
    result = await session.execute(
        select(BadgeAwardDB).where(
            BadgeAwardDB.badge_id == badge_id,
            BadgeAwardDB.tenant_id == tenant_id,
        )
    )

    return result.scalar_one_or_none()


async def save_award(
    session: AsyncSession,
    badge_id: str,
    tenant_id: str,
    evidence_ref: str | None = None,
) -> BadgeAwardDB:
    existing_award = await find_award(
        session,
        badge_id,
        tenant_id,
    )

    if existing_award is not None:
        return existing_award

    award = BadgeAwardDB(
        badge_id=badge_id,
        tenant_id=tenant_id,
        awarded_at=datetime.now(timezone.utc),
        evidence_ref=evidence_ref,
    )

    session.add(award)

    try:
        await session.commit()
        await session.refresh(award)
    except Exception:
        await session.rollback()

        existing_award = await find_award(
            session,
            badge_id,
            tenant_id,
        )

        if existing_award is not None:
            return existing_award

        raise

    return award


async def find_awards(
    session: AsyncSession,
    tenant_id: str,
) -> list[BadgeAwardDB]:
    result = await session.execute(
        select(BadgeAwardDB)
        .where(BadgeAwardDB.tenant_id == tenant_id)
        .order_by(BadgeAwardDB.awarded_at)
    )

    return list(result.scalars().all())
