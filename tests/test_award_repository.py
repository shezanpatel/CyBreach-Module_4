from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.award_repository import find_award, find_awards, save_award
from app.award_models import BadgeAwardDB


@pytest.mark.asyncio
async def test_find_award_returns_existing_award():
    session = AsyncMock()

    award = BadgeAwardDB(
        badge_id="streak_7_day",
        tenant_id="tenant_001",
        awarded_at=datetime(2026, 10, 6, 10, 0),
        evidence_ref="mod2:rule123:tenant_001:run001",
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = award
    session.execute.return_value = result

    found = await find_award(
        session,
        "streak_7_day",
        "tenant_001",
    )

    assert found is award
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_award_returns_none_when_missing():
    session = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found = await find_award(
        session,
        "streak_7_day",
        "tenant_001",
    )

    assert found is None


@pytest.mark.asyncio
async def test_save_award_returns_existing_award():
    session = AsyncMock()

    existing_award = BadgeAwardDB(
        badge_id="streak_7_day",
        tenant_id="tenant_001",
        awarded_at=datetime(2026, 10, 6, 10, 0),
        evidence_ref="mod2:rule123:tenant_001:run001",
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_award
    session.execute.return_value = result

    saved = await save_award(
        session,
        "streak_7_day",
        "tenant_001",
        "mod2:rule123:tenant_001:run001",
    )

    assert saved is existing_award
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_award_creates_new_award():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    new_award = await save_award(
        session,
        "streak_7_day",
        "tenant_001",
        "mod2:rule123:tenant_001:run001",
    )

    assert new_award.badge_id == "streak_7_day"
    assert new_award.tenant_id == "tenant_001"
    assert new_award.evidence_ref == "mod2:rule123:tenant_001:run001"

    session.add.assert_called_once_with(new_award)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(new_award)

@pytest.mark.asyncio
async def test_find_awards_returns_tenant_awards():
    session = MagicMock()
    session.execute = AsyncMock()

    award_1 = BadgeAwardDB(
        badge_id="badge_7_day_streak",
        tenant_id="tenant_001",
        awarded_at=datetime(2026, 10, 6, 10, 0),
        evidence_ref="mod2:rule123:tenant_001:run001",
    )

    award_2 = BadgeAwardDB(
        badge_id="badge_30_day_streak",
        tenant_id="tenant_001",
        awarded_at=datetime(2026, 10, 7, 10, 0),
        evidence_ref="mod3:streak:tenant_001:milestone001",
    )

    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        award_1,
        award_2,
    ]

    session.execute.return_value = result

    awards = await find_awards(
        session,
        "tenant_001",
    )

    assert awards ==[award_1, award_2]
    session.execute.assert_awaited_once()