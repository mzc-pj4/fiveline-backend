from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, default=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    created_at: datetime
    product_name: str | None = None
    product_price: Decimal | None = None
    line_total: Decimal | None = None


class CartView(BaseModel):
    items: list[CartItemPublic]
    total_price: Decimal
