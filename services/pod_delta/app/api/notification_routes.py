from typing import Optional
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
)

from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationUpdate,
    NotificationStatusUpdate,
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    BulkOperationResponse,
    BulkNotificationUpdate,
    NotificationStatsResponse,
)

from app.services.notification_service import (
    get_all_notifications,
    get_notifications_by_user,
    get_unread_notifications,
    get_unread_count,
    get_notification_stats,
    create_notification,
    update_notification,
    delete_notification,
    mark_notification_as_read,
    update_notification_status,
    bulk_mark_as_read,
    bulk_delete,
)

from app.core.exceptions import NotificationNotFoundError


router = APIRouter(
    tags=["Notifications"]
)


# ============================================================
# GET ALL NOTIFICATIONS
# ============================================================

@router.get(
    "/",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get All Notifications",
    description="Returns all notifications with pagination and filtering.",
)
def read_notifications(
    skip: int = Query(
        0,
        ge=0,
        description="Number of records to skip",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Number of records to return",
    ),
    user_id: Optional[int] = Query(
        None,
        description="Filter by user ID",
    ),
    notification_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by notification status",
    ),
    channel: Optional[str] = Query(
        None,
        description="Filter by channel",
    ),
    priority: Optional[str] = Query(
        None,
        description="Filter by priority",
    ),
    is_read: Optional[bool] = Query(
        None,
        description="Filter by read status",
    ),
    search: Optional[str] = Query(
        None,
        description="Search in title and message",
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter by start date",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter by end date",
    ),
    sort_by: str = Query(
        "created_at",
        description="Sort field",
    ),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order",
    ),
    db: Session = Depends(get_db),
):
    return get_all_notifications(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        status=notification_status,
        channel=channel,
        priority=priority,
        is_read=is_read,
        search=search,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ============================================================
# GET USER NOTIFICATIONS
# ============================================================

@router.get(
    "/user/{user_id}",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Notifications",
    description="Returns all notifications for a specific user with pagination.",
)
def read_user_notifications(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_read: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    return get_notifications_by_user(
        db,
        user_id,
        skip=skip,
        limit=limit,
        is_read=is_read,
    )


# ============================================================
# GET UNREAD NOTIFICATIONS
# ============================================================

@router.get(
    "/unread",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Unread Notifications",
    description="Returns all unread notifications with pagination.",
)
def read_unread_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return get_unread_notifications(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
    )


# ============================================================
# GET UNREAD COUNT
# ============================================================

@router.get(
    "/unread/count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Unread Notification Count",
    description="Returns the total number of unread notifications.",
)
def unread_notification_count(
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return get_unread_count(
        db,
        user_id=user_id,
    )


# ============================================================
# GET NOTIFICATION STATISTICS
# ============================================================

@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Notification Statistics",
    description="Returns statistics about notifications for analytics.",
)
def get_stats(
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return get_notification_stats(
        db,
        user_id=user_id,
    )


# ============================================================
# CREATE NOTIFICATION
# ============================================================

@router.post(
    "/",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Notification",
    description="Creates a new notification.",
)
def add_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
):
    return create_notification(
        db,
        notification,
    )


# ============================================================
# BULK MARK AS READ
# IMPORTANT: This must come BEFORE /{notification_id}
# ============================================================

@router.patch(
    "/bulk/read",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Multiple Notifications as Read",
    description="Marks multiple notifications as read in bulk.",
)
def bulk_mark_read(
    bulk_update: BulkNotificationUpdate,
    db: Session = Depends(get_db),
):
    return bulk_mark_as_read(
        db,
        bulk_update.notification_ids,
    )


# ============================================================
# BULK DELETE
# IMPORTANT: This must come BEFORE /{notification_id}
# ============================================================

@router.delete(
    "/bulk",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Multiple Notifications",
    description="Deletes multiple notifications in bulk.",
)
def bulk_delete_notifications(
    bulk_update: BulkNotificationUpdate,
    db: Session = Depends(get_db),
):
    return bulk_delete(
        db,
        bulk_update.notification_ids,
    )


# ============================================================
# UPDATE NOTIFICATION
# ============================================================

@router.put(
    "/{notification_id}",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Notification",
    description="Updates an existing notification.",
)
def update_notification_route(
    notification_id: int,
    notification: NotificationUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_notification(
            db,
            notification_id,
            notification,
        )

    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found",
        )


# ============================================================
# DELETE NOTIFICATION
# ============================================================

@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Notification",
    description="Deletes a notification by its ID.",
)
def delete_notification_route(
    notification_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_notification(
            db,
            notification_id,
        )

        return {
            "message": "Notification deleted successfully"
        }

    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found",
        )


# ============================================================
# MARK NOTIFICATION AS READ
# ============================================================

@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Read",
    description="Marks a notification as read.",
)
def mark_notification_read_route(
    notification_id: int,
    db: Session = Depends(get_db),
):
    try:
        return mark_notification_as_read(
            db,
            notification_id,
        )

    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found",
        )


# ============================================================
# UPDATE NOTIFICATION STATUS
# ============================================================

@router.patch(
    "/{notification_id}/status",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Notification Status",
    description="Updates the status of a notification.",
)
def update_status(
    notification_id: int,
    status_update: NotificationStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_notification_status(
            db,
            notification_id,
            status_update.status,
        )

    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found",
        )