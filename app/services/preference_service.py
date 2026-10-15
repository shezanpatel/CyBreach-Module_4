from sqlalchemy.orm import Session

from app.models.notification_preference import NotificationPreference

from app.schemas.preference_schema import (
    PreferenceCreate,
    PreferenceUpdate,
)


def create_preferences(
    db: Session,
    preference: PreferenceCreate,
):
    """Create notification preferences for a user."""

    existing = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == preference.user_id
        )
        .first()
    )

    if existing:
        return {"message": "Preferences already exist"}

    new_preference = NotificationPreference(
        user_id=preference.user_id,

        # Channel preferences
        email_enabled=preference.email_enabled,
        sms_enabled=preference.sms_enabled,
        in_app_enabled=preference.in_app_enabled,
        push_enabled=preference.push_enabled,
        webhook_enabled=preference.webhook_enabled,
        whatsapp_enabled=preference.whatsapp_enabled,
        telegram_enabled=preference.telegram_enabled,

        # Priority preferences
        receive_low_priority=preference.receive_low_priority,
        receive_medium_priority=preference.receive_medium_priority,
        receive_high_priority=preference.receive_high_priority,
        receive_urgent_priority=preference.receive_urgent_priority,
        receive_critical_priority=preference.receive_critical_priority,

        # Quiet hours
        quiet_hours_enabled=preference.quiet_hours_enabled,
        quiet_hours_start=preference.quiet_hours_start,
        quiet_hours_end=preference.quiet_hours_end,

        # Digest / frequency
        digest_enabled=preference.digest_enabled,
        frequency=preference.frequency,

        # Unsubscribe
        is_unsubscribed_all=preference.is_unsubscribed_all,
    )

    db.add(new_preference)
    db.commit()
    db.refresh(new_preference)

    return new_preference


def get_preferences(
    db: Session,
    user_id: int,
):
    """Get notification preferences for a user."""

    return (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == user_id
        )
        .first()
    )


def update_preferences(
    db: Session,
    user_id: int,
    preference: PreferenceUpdate,
):
    """Update only the preference fields provided by the user."""

    existing = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == user_id
        )
        .first()
    )

    if existing is None:
        return None

    # Get only fields actually supplied in the request
    update_data = preference.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(existing, field, value)

    db.commit()
    db.refresh(existing)

    return existing