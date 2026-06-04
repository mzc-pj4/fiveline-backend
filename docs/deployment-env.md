# Deployment Environment

This project deploys the frontend to S3 + CloudFront and the backend services to EKS.
RDS PostgreSQL is the shared database, separated by service-owned schemas.

## Backend runtime split

Local Docker Compose now reads values from the repository-root `.env` file.
Use `.env.example` as the local template:

```bash
cp .env.example .env
docker compose up --build
```

Do not commit `.env`. It is ignored because it can contain secrets.
Also avoid sharing raw `docker compose config` output, because Docker prints the resolved secret values after interpolation.

Use Kubernetes `Secret` for sensitive values:

```text
DATABASE_URL=postgresql+psycopg://aiops:<password>@<rds-endpoint>:5432/aiops
JWT_SECRET=<long-random-secret>
```

Use Kubernetes `ConfigMap` for non-sensitive values:

```text
ENVIRONMENT=dev
LOG_LEVEL=INFO
JWT_ALGORITHM=HS256
```

Service-specific config:

```text
user-service
SERVICE_NAME=user-service
DB_SCHEMA=user_schema
JWT_EXPIRE_MINUTES=60

product-service
SERVICE_NAME=product-service
DB_SCHEMA=product_schema

order-service
SERVICE_NAME=order-service
DB_SCHEMA=order_schema
PRODUCT_SERVICE_URL=http://product-service:8000
PRODUCT_SERVICE_TIMEOUT_S=3.0
FAILURE_RATE=0.05
SLOW_RATE=0.03
SLOW_RESPONSE_MS_MIN=1500
SLOW_RESPONSE_MS_MAX=3500
```

## RDS layout

Create one PostgreSQL database:

```text
database: aiops
schemas: user_schema, product_schema, order_schema
```

Each service connects to the same RDS database but sets its own `DB_SCHEMA`.
Alembic migrations create the tables inside the matching schema.

## EKS service routing

The ALB Ingress should route API paths to the right Kubernetes Service:

```text
/api/auth/*      -> user-service
/api/products/*  -> product-service
/api/cart/*      -> order-service
/api/orders/*    -> order-service
/api/error-test  -> order-service
/api/slow-test   -> order-service
```

CloudFront should forward `/api/*` to this ALB origin and serve all other paths from the frontend S3 origin.

## Docker build behavior

The backend Dockerfiles install from service-level `requirements.txt` files.
Those files are generated with `pip-compile`, so Docker builds use pinned Python dependency versions.
