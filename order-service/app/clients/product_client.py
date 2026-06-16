from decimal import Decimal

import httpx

from app.core.config import settings

# 모듈 레벨 공유 클라이언트 — TCP 연결 재사용 (keep-alive)
_client = httpx.Client(
    timeout=settings.product_service_timeout_s,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
)


class ProductInfo:
    def __init__(self, id: int, name: str, price: Decimal) -> None:
        self.id = id
        self.name = name
        self.price = price


class ProductClientError(Exception):
    pass


class ProductNotFound(ProductClientError):
    pass


def get_product(product_id: int) -> ProductInfo:
    url = f"{settings.product_service_url}/api/products/{product_id}"
    try:
        response = _client.get(url)
    except httpx.HTTPError as exc:
        raise ProductClientError(f"product-service unreachable: {exc}") from exc

    if response.status_code == 404:
        raise ProductNotFound(f"product {product_id} not found")
    if response.status_code >= 400:
        raise ProductClientError(f"product-service error {response.status_code}: {response.text}")

    data = response.json()
    return ProductInfo(
        id=data["id"],
        name=data["name"],
        price=Decimal(str(data["price"])),
    )
