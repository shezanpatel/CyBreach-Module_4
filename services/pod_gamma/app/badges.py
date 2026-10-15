import json
from pathlib import Path

from app.models import UserProfile

DEFAULT_BADGE_CONFIG = (
    
    Path(__file__).resolve().parent.parent / "config" / "badges.json"
)

def load_badge_definitions(config_path: Path = DEFAULT_BADGE_CONFIG) -> dict[int, str]:
    with config_path.open("r", encoding="utf-8") as config_file:
        definitions = json.load(config_file)

    return {int(streak): badge_id for streak, badge_id in definitions.items()}


def award_milestone_badge(user: UserProfile) -> UserProfile:
    badge_definitions = load_badge_definitions()

    reached_badges = [
        (streak, badge_id)
        for streak, badge_id in badge_definitions.items()
        if user.current_streak >= streak
    ]

    if reached_badges:
        highest_streak, badge_id = max(reached_badges)

        if badge_id not in user.badges:
            user.badges.append(badge_id)

    return user

def reveal_hidden_badge(
    user: UserProfile,
    badge_id: str,
    required_streak: int,
) -> UserProfile:
    """
    Reveal a hidden badge only after the required verified streak is reached.
    """

    if user.current_streak >= required_streak:
        if badge_id not in user.badges:
            user.badges.append(badge_id)

    return user