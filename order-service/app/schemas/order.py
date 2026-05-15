from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
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
