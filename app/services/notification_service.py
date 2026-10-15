from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.notification import Notification

from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationUpdate,
    NotificationStatus,
    NotificationChannel,
    NotificationPriority,
)

from app.core.exceptions import NotificationNotFoundError


def get_all_notifications(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    priority: Optional[str] = None,
    is_read: Optional[bool] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Dict[str, Any]:
    """Get all notifications with pagination and filtering."""

    query = db.query(Notification)

    # Filters
    if user_id is not None:
        query = query.filter(Notification.user_id == user_id)

    if status is not None:
        query = query.filter(Notification.status == status)

    if channel is not None:
        query = query.filter(Notification.channel == channel)

    if priority is not None:
        query = query.filter(Notification.priority == priority)

    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    if search:
        query = query.filter(
            or_(
                Notification.title.ilike(f"%{search}%"),
                Notification.message.ilike(f"%{search}%"),
            )
        )

    if start_date:
        query = query.filter(
            Notification.created_at >= start_date
        )

    if end_date:
        query = query.filter(
            Notification.created_at <= end_date
        )

    # Count before pagination
    total = query.count()

    # Safe sorting
    allowed_sort_fields = {
        "created_at": Notification.created_at,
        "updated_at": Notification.updated_at,
        "priority": Notification.priority,
        "status": Notification.status,
        "title": Notification.title,
    }

    sort_column = allowed_sort_fields.get(
        sort_by,
        Notification.created_at
    )

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Pagination
    notifications = (
        query
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "notifications": notifications,
    }


def get_notifications_by_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    is_read: Optional[bool] = None,
) -> Dict[str, Any]:
    """Get notifications for a specific user."""

    query = db.query(Notification).filter(
        Notification.user_id == user_id
    )

    if is_read is not None:
        query = query.filter(
            Notification.is_read == is_read
        )

    total = query.count()

    notifications = (
        query
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "notifications": notifications,
    }


def get_unread_notifications(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get all unread notifications."""

    query = db.query(Notification).filter(
        Notification.is_read.is_(False)
    )

    if user_id is not None:
        query = query.filter(
            Notification.user_id == user_id
        )

    total = query.count()

    notifications = (
        query
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "notifications": notifications,
    }


def get_unread_count(
    db: Session,
    user_id: Optional[int] = None,
) -> Dict[str, int]:
    """Get count of unread notifications."""

    query = db.query(Notification).filter(
        Notification.is_read.is_(False)
    )

    if user_id is not None:
        query = query.filter(
            Notification.user_id == user_id
        )

    return {
        "count": query.count()
    }


def get_notification_stats(
    db: Session,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get notification statistics for analytics."""

    query = db.query(Notification)

    if user_id is not None:
        query = query.filter(
            Notification.user_id == user_id
        )

    total = query.count()

    unread = query.filter(
        Notification.is_read.is_(False)
    ).count()

    read = query.filter(
        Notification.is_read.is_(True)
    ).count()

    # Statistics by channel
    by_channel = {}

    for channel in NotificationChannel:
        count = query.filter(
            Notification.channel == channel
        ).count()

        if count > 0:
            by_channel[channel.value] = count

    # Statistics by priority
    by_priority = {}

    for priority in NotificationPriority:
        count = query.filter(
            Notification.priority == priority
        ).count()

        if count > 0:
            by_priority[priority.value] = count

    # Statistics by status
    by_status = {}

    for notification_status in NotificationStatus:
        count = query.filter(
            Notification.status == notification_status
        ).count()

        if count > 0:
            by_status[notification_status.value] = count

    return {
        "total": total,
        "unread": unread,
        "read": read,
        "by_channel": by_channel,
        "by_priority": by_priority,
        "by_status": by_status,
    }


def create_notification(
    db: Session,
    notification_data: NotificationCreate,
) -> Notification:
    """Create a new notification."""

    new_notification = Notification(
        user_id=notification_data.user_id,
        title=notification_data.title,
        message=notification_data.message,
        channel=notification_data.channel,
        priority=notification_data.priority,
        status=NotificationStatus.PENDING,
    )

    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)

    return new_notification


def update_notification(
    db: Session,
    notification_id: int,
    updated_data: NotificationUpdate,
) -> Notification:
    """Update an existing notification."""

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )

    if notification is None:
        raise NotificationNotFoundError(
            f"Notification {notification_id} not found"
        )

    if updated_data.title is not None:
        notification.title = updated_data.title

    if updated_data.message is not None:
        notification.message = updated_data.message

    if updated_data.channel is not None:
        notification.channel = updated_data.channel

    if updated_data.priority is not None:
        notification.priority = updated_data.priority

    db.commit()
    db.refresh(notification)

    return notification


def delete_notification(
    db: Session,
    notification_id: int,
) -> None:
    """Delete a notification."""

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )

    if notification is None:
        raise NotificationNotFoundError(
            f"Notification {notification_id} not found"
        )

    db.delete(notification)
    db.commit()


def mark_notification_as_read(
    db: Session,
    notification_id: int,
) -> Notification:
    """Mark notification as read."""

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )

    if notification is None:
        raise NotificationNotFoundError(
            f"Notification {notification_id} not found"
        )

    notification.mark_as_read()

    db.commit()
    db.refresh(notification)

    return notification


def update_notification_status(
    db: Session,
    notification_id: int,
    status: NotificationStatus,
) -> Notification:
    """Update notification status."""

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )

    if notification is None:
        raise NotificationNotFoundError(
            f"Notification {notification_id} not found"
        )

    notification.status = status

    db.commit()
    db.refresh(notification)

    return notification


def bulk_mark_as_read(
    db: Session,
    notification_ids: List[int],
) -> Dict[str, Any]:
    """Mark multiple notifications as read in bulk."""

    updated = 0
    failed = 0
    failed_ids = []

    for notification_id in notification_ids:

        try:
            notification = (
                db.query(Notification)
                .filter(Notification.id == notification_id)
                .first()
            )

            if notification:
                notification.mark_as_read()
                updated += 1
            else:
                failed += 1
                failed_ids.append(notification_id)

        except Exception:
            failed += 1
            failed_ids.append(notification_id)

    db.commit()

    return {
        "success": failed == 0,
        "processed_count": updated + failed,
        "failed_count": failed,
        "failed_ids": failed_ids if failed_ids else None,
        "message": (
            f"Successfully marked "
            f"{updated} notifications as read"
        ),
    }


def bulk_delete(
    db: Session,
    notification_ids: List[int],
) -> Dict[str, Any]:
    """Delete multiple notifications in bulk."""

    deleted = 0
    failed = 0
    failed_ids = []

    for notification_id in notification_ids:

        try:
            notification = (
                db.query(Notification)
                .filter(Notification.id == notification_id)
                .first()
            )

            if notification:
                db.delete(notification)
                deleted += 1
            else:
                failed += 1
                failed_ids.append(notification_id)

        except Exception:
            failed += 1
            failed_ids.append(notification_id)

    db.commit()

    return {
        "success": failed == 0,
        "processed_count": deleted + failed,
        "failed_count": failed,
        "failed_ids": failed_ids if failed_ids else None,
        "message": (
            f"Successfully deleted "
            f"{deleted} notifications"
        ),
    }