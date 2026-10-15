from datetime import datetime

from app.models import UserProfile


def update_streak(
    user: UserProfile,
    current_time: datetime,
) -> UserProfile:
    if user.verified_activity_time is None:
       return user

    if user.last_completion_time is None:
        user.current_streak = 1
        user.last_completion_time = current_time
        return user

    time_gap = current_time - user.last_completion_time
    hours_passed = time_gap.total_seconds() / 3600

    if hours_passed < 24:
        return user

    if hours_passed <= 48:
        user.current_streak += 1
    else:
        user.current_streak = 1

    user.last_completion_time = current_time
    return user