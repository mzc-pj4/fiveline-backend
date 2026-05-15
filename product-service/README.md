# product-service

team4-aiops 상품·리뷰 마이크로서비스.

## 엔드포인트

- `GET /api/products` — 목록·검색 (`?keyword=`, `?category=`, `?limit=`, `?offset=`)
- `GET /api/products/{id}` — 상세 (평균 별점·리뷰 수는 목록에서만 제공)
- `POST /api/products` — 생성 (W2 dev 편의용, W3에 admin 보호)
- `GET /api/products/{id}/reviews` — 리뷰 목록
- `POST /api/products/{id}/reviews` — 리뷰 작성 (JWT 필요)
- `GET /api/health`

## 스키마

`product_schema` — 테이블: `products`, `reviews`.

## 마이그레이션

```bash
docker compose exec product-service alembic revision --autogenerate -m "init products and reviews"
docker compose exec product-service alembic upgrade head
```

## 발생 이벤트

- `PRODUCT_LIST_VIEW`
- `PRODUCT_SEARCH`
- `PRODUCT_VIEW`
- `REVIEW_CREATED`
- `REVIEW_FAILED`
