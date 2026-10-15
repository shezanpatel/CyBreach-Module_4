from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.user_models import UserProfileDB


async def find_user(
    session: AsyncSession,
    user_id: str,
    tenant_id: str,
) -> UserProfileDB | None:
    result = await session.execute(
        select(UserProfileDB).where(
            UserProfileDB.user_id == user_id,
            UserProfileDB.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def save_user(
    session: AsyncSession,
    user_id: str,
    tenant_id: str = "default",
    current_streak: int = 0,
    last_completion_time: datetime | None = None,
    verified_activity_time: datetime | None = None,
) -> UserProfileDB:
    existing_user = await find_user(
        session,
        user_id,
        tenant_id,
    )

    if existing_user is not None:
        existing_user.current_streak = current_streak
        existing_user.last_completion_time = last_completion_time
        existing_user.verified_activity_time = verified_activity_time

        await session.commit()
        await session.refresh(existing_user)

        return existing_user

    user = UserProfileDB(
        user_id=user_id,
        tenant_id=tenant_id,
        current_streak=current_streak,
        last_completion_time=last_completion_time,
        verified_activity_time=verified_activity_time,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user