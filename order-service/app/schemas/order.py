from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DirectOrderCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, default=1)


class OrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    price: Decimal


class OrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_price: Decimal
    status: str
    error_code: str | None
    response_time_ms: int | None
    created_at: datetime
    items: list[OrderItemPublic]


class OrderCreateResult(BaseModel):
    order: OrderPublic
    succeeded: bool
