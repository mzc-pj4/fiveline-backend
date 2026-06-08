from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser, get_current_user
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationPublic

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=dict)
def list_notifications(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    stmt = select(Notification).where(Notification.user_id == current_user.user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    unread_count = db.execute(
        select(func.count()).where(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
    ).scalar_one()

    offset = (page - 1) * size
    rows = db.execute(stmt.order_by(Notification.created_at.desc()).limit(size).offset(offset)).scalars().all()

    return {
        "items": [NotificationPublic.model_validate(r) for r in rows],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "size": size,
    }


@router.post("/read/{notification_id}", status_code=status.HTTP_200_OK)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "notification not found")
    notification.is_read = True
    db.commit()
    return {"message": "marked as read"}


@router.post("/internal", response_model=NotificationPublic, status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db)):
    notification = Notification(
        user_id=payload.user_id,
        type=payload.type,
        title=payload.title,
        message=payload.message,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return NotificationPublic.model_validate(notification)
