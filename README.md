# fiveline-backend

team mzc-pj4 / fiveline — AWS AI 기반 인프라 운영·비용 분석 플랫폼의 **백엔드** 모노레포.

| 영역 | 폴더 |
|---|---|
| 샘플 이커머스 마이크로서비스 (FastAPI × 3) | `user-service/`, `product-service/`, `order-service/` |
| 로컬 개발 환경 | `docker-compose.yml`, `infra/postgres-init.sql` |
| 운영 플랫폼 placeholder | `platform/` (Glue Job, Lambda 등 W4~W7) |
| 아키텍처·운영 문서 | `docs/`, `CLAUDE.md` |

프론트엔드는 별도 repo: [fiveline-frontend](https://github.com/mzc-pj4/fiveline-frontend)

## 빠른 시작 — 백엔드 로컬 개발

전제: Docker Desktop 실행 중.

```powershell
docker compose up --build
```

뜨는 컨테이너:
- `postgres` (5432) — schema 3개 분리 (user/product/order)
- `adminer` (8080) — DB GUI
- `user-service` (8001) — auth, signup, login, JWT
- `product-service` (8002) — 상품, 리뷰, 검색
- `order-service` (8003) — 장바구니, 주문, 실패·지연 시뮬레이션

처음 띄울 때 — 마이그레이션 + 시드:

```powershell
# user
docker compose exec user-service alembic revision --autogenerate -m "init users"
docker compose exec user-service alembic upgrade head

# product
docker compose exec product-service alembic revision --autogenerate -m "init products reviews"
docker compose exec product-service alembic upgrade head
docker compose exec product-service python scripts/seed.py

# order
docker compose exec order-service alembic revision --autogenerate -m "init cart orders"
docker compose exec order-service alembic upgrade head
```

각 서비스 Swagger:
- http://localhost:8001/docs
- http://localhost:8002/docs
- http://localhost:8003/docs

## AWS 인프라

- 인프라 IaC는 별도 Terraform 레포에서 관리 (S3/DynamoDB 백엔드 포함 미적용)
- 목표 state backend: S3 `mzc-pj4-tfstate-089955620282`, DynamoDB `mzc-pj4-tflock`

상세: [docs/architecture.md](docs/architecture.md)

## 8주 일정 위치

W2 — 샘플 워크로드 구현 (현재 단계). 다음 W3에서 EKS + ArgoCD로 배포 파이프라인.

## 기술 스택

- Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
- PostgreSQL 16 (서비스별 스키마 분리)
- Terraform 1.7+ (AWS provider v5/v6)
- Docker Compose (로컬 dev)
- 예정: ECR / EKS / Helm / ArgoCD / Bedrock Agent / Athena / Glue

## 발생 서비스 이벤트

각 서비스가 stdout으로 JSON 구조화 로그를 발생시킴 (W4 데이터 파이프라인의 원료):

- `USER_SIGNUP`, `USER_LOGIN`, `USER_LOGIN_FAILED`
- `PRODUCT_LIST_VIEW`, `PRODUCT_SEARCH`, `PRODUCT_VIEW`, `REVIEW_CREATED`, `REVIEW_FAILED`
- `CART_ITEM_ADDED`, `CART_VIEWED`, `CART_ITEM_UPDATED`, `CART_ITEM_REMOVED`
- `ORDER_FROM_CART`, `ORDER_SUCCESS`, `ORDER_FAILED`, `SLOW_RESPONSE`, `API_ERROR`
- 모든 요청에 `ACCESS_LOG` (api_path, status_code, response_time_ms, trace_id)
