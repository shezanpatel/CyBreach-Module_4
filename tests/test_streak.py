from datetime import datetime, timedelta

from app.models import UserProfile
from app.streak import update_streak
from freezegun import freeze_time
from app.badges import award_milestone_badge, reveal_hidden_badge

def test_first_completion_starts_streak():
    current_time = datetime(2026, 7, 10, 10, 0)

    user = UserProfile(
        user_id="user_001",
        verified_activity_time=current_time,
    )

    updated_user = update_streak(user, current_time)

    assert updated_user.current_streak == 1
    assert updated_user.last_completion_time == current_time

def test_completion_under_24_hours_is_ignored():
    start_time = datetime(2026, 7, 10, 10, 0)

    user = UserProfile(
        user_id="user_001",
        current_streak=1,
        last_completion_time=start_time,
        verified_activity_time=start_time,
    )

    current_time = start_time + timedelta(hours=10)

    updated_user = update_streak(user, current_time)

    assert updated_user.current_streak == 1
    assert updated_user.last_completion_time == start_time  
def test_completion_between_24_and_48_hours_increases_streak():
    start_time = datetime(2026, 7, 10, 10, 0)

    user = UserProfile(
        user_id="user_001",
        current_streak=1,
        last_completion_time=start_time,
         verified_activity_time=start_time,
    )

    current_time = start_time + timedelta(hours=24)

    updated_user = update_streak(user, current_time)

    assert updated_user.current_streak == 2
    assert updated_user.last_completion_time == current_time      
def test_completion_over_48_hours_resets_streak():
    start_time = datetime(2026, 7, 10, 10, 0)

    user = UserProfile(
        user_id="user_001",
        current_streak=1,
        last_completion_time=start_time,
        verified_activity_time=start_time,
    )

    current_time = start_time + timedelta(hours=49)

    updated_user = update_streak(user, current_time)

    assert updated_user.current_streak == 1
    assert updated_user.last_completion_time == current_time    
def test_seven_day_streak_awards_badge():
    user = UserProfile(
        user_id="user_001",
        current_streak=7,
    )

    updated_user = award_milestone_badge(user)

    assert "badge_7_day_streak" in updated_user.badges    
def test_duplicate_badge_is_not_added():
    user = UserProfile(
        user_id="user_001",
        current_streak=7,
        badges=["badge_7_day_streak"],
    )

    updated_user = award_milestone_badge(user)

    assert updated_user.badges.count("badge_7_day_streak") == 1    
def test_seven_day_streak_using_time_simulation():
    user = UserProfile(
    user_id="user_001",
    verified_activity_time=datetime(2026, 7, 1, 10, 0),
)
    
    with freeze_time("2026-07-01 10:00:00") as frozen_time:
        for day in range(7):
            current_time = datetime.now()
            update_streak(user, current_time)
            award_milestone_badge(user)

            if day < 6:
                frozen_time.tick(delta=timedelta(hours=24))

    assert user.current_streak == 7
    assert "badge_7_day_streak" in user.badges


def test_hidden_badge_is_revealed_at_required_streak():
    user = UserProfile(
        user_id="user_001",
        current_streak=100,
    )

    updated_user = reveal_hidden_badge(
        user,
        "badge_hidden_100_streak",
        100,
    )

    assert "badge_hidden_100_streak" in updated_user.badges


   