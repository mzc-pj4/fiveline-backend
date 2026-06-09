from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=2000)


class ReviewPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    user_id: int
    reviewer_name: str | None = None
    rating: int
    content: str
    created_at: datetime
