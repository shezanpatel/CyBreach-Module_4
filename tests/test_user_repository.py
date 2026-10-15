from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.user_models import UserProfileDB
from app.user_repository import find_user, save_user


@pytest.mark.asyncio
async def test_find_user_returns_existing_user():
    session = AsyncMock()

    user = UserProfileDB(
        user_id="user_001",
        tenant_id="tenant_001",
        current_streak=7,
        last_completion_time=datetime(2026, 10, 6, 10, 0),
        verified_activity_time=datetime(2026, 10, 6, 10, 0),
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute.return_value = result

    found = await find_user(
        session,
        "user_001",
        "tenant_001",
    )

    assert found is user
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_user_returns_none_when_missing():
    session = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found = await find_user(
        session,
        "user_001",
        "tenant_001",
    )

    assert found is None


@pytest.mark.asyncio
async def test_save_user_creates_new_user():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    user = await save_user(
        session,
        "user_001",
        "tenant_001",
        current_streak=7,
    )

    assert user.user_id == "user_001"
    assert user.tenant_id == "tenant_001"
    assert user.current_streak == 7

    session.add.assert_called_once_with(user)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_save_user_updates_existing_user():
    session = AsyncMock()

    existing_user = UserProfileDB(
        user_id="user_001",
        tenant_id="tenant_001",
        current_streak=6,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_user
    session.execute.return_value = result

    updated = await save_user(
        session,
        "user_001",
        "tenant_001",
        current_streak=7,
    )

    assert updated is existing_user
    assert updated.current_streak == 7

    session.add.assert_not_called()
    session.commit.assert_awaited_once()