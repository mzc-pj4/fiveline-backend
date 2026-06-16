# order-service

mzc-pj4 장바구니·주문 마이크로서비스. 운영 분석용 실패·지연 시뮬레이션 포함.

## 엔드포인트

- `POST /api/cart/items` — 장바구니 추가 (JWT)
- `GET  /api/cart` — 장바구니 조회 (JWT)
- `PATCH /api/cart/items/{id}` — 수량 변경 (JWT)
- `DELETE /api/cart/items/{id}` — 삭제 (JWT)
- `POST /api/orders/from-cart` — 장바구니 → 주문 (JWT, 실패·지연 시뮬레이션 포함)
- `GET  /api/orders/me` — 내 주문 내역 (JWT)
- `GET  /api/error-test` — 항상 500 (운영 분석용 합성 에러)
- `GET  /api/slow-test` — 2~4초 지연 (slow response 감지 데모용)
- `GET  /api/health`

## 스키마

`order_schema` — 테이블: `cart_items`, `orders`, `order_items`.

## 다른 서비스 호출

`product-service` 의 `GET /api/products/{id}` 를 HTTP로 호출 (재고·가격 확인용).
환경변수 `PRODUCT_SERVICE_URL` 로 주소 지정 (docker-compose 안에서는 `http://product-service:8000`).

## 실패·지연 시뮬레이션

`FAILURE_RATE` (기본 0.05), `SLOW_RATE` (기본 0.03) 환경변수로 조정.

실패 코드: `OUT_OF_STOCK`, `PAYMENT_FAILED_SIMULATED`, `DB_TIMEOUT`, `INTERNAL_SERVER_ERROR`.

## 마이그레이션

```bash
docker compose exec order-service alembic revision --autogenerate -m "init cart orders"
docker compose exec order-service alembic upgrade head
```

## 발생 이벤트

- `CART_ITEM_ADDED`, `CART_VIEWED`, `CART_ITEM_UPDATED`, `CART_ITEM_REMOVED`
- `ORDER_FROM_CART`, `ORDER_SUCCESS`, `ORDER_FAILED`
- `API_ERROR`, `SLOW_RESPONSE` (미들웨어에서 자동)

## 액세스 로그

모든 요청에 대해 자동 JSON 액세스 로그 (`api_path`, `http_method`, `status_code`, `response_time_ms`, `trace_id`).

<!-- aiops-review 파이프라인 동작 확인용 테스트 변경 -->

