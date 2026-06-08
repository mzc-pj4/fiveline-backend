from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationCreate(BaseModel):
    user_id: int
    type: str
    title: str
    message: str


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
