from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str = Field(min_length=1, max_length=50)
    brand: str | None = Field(default=None, max_length=100)
    price: Decimal = Field(ge=0)
    original_price: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int = Field(ge=0, default=0)
    image_url: str | None = None


class ProductPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    category: str
    brand: str | None
    price: Decimal
    original_price: Decimal | None
    stock_quantity: int
    image_url: str | None
    created_at: datetime


class ProductListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    brand: str | None
    price: Decimal
    original_price: Decimal | None
    stock_quantity: int
    image_url: str | None
    average_rating: float | None = None
    review_count: int = 0


class ProductList(BaseModel):
    items: list[ProductListItem]
    total: int
    page: int
    size: int
