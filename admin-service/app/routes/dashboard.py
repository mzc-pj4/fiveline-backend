import json
import os
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.deps import CurrentUser, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")


def _get_aws_account_id() -> str:
    try:
        return boto3.client("sts", region_name=_REGION).get_caller_identity()["Account"]
    except Exception:
        return ""


_ACCOUNT_ID = _get_aws_account_id()


@router.get(
    "/ops-data",
    responses={
        503: {"description": "DASHBOARD_BUCKET 미설정 또는 S3 오류"},
        404: {"description": "데이터가 아직 준비되지 않았습니다"},
    },
)
def get_ops_data(_: Annotated[CurrentUser, Depends(require_admin)]):
    bucket = os.environ.get("DASHBOARD_BUCKET", "")
    if not bucket:
        raise HTTPException(status_code=503, detail="DASHBOARD_BUCKET not configured")
    try:
        s3 = boto3.client("s3", region_name=_REGION)
        get_kwargs: dict = {"Bucket": bucket, "Key": "data.json"}
        if _ACCOUNT_ID:
            get_kwargs["ExpectedBucketOwner"] = _ACCOUNT_ID
        obj = s3.get_object(**get_kwargs)
        return json.loads(obj["Body"].read())
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchKey", "NoSuchBucket"):
            raise HTTPException(status_code=404, detail="데이터가 아직 준비되지 않았습니다")
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/dashboard")
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    order_stats = db.execute(text(f"""
        SELECT
            COUNT(*) as total_orders,
            COALESCE(SUM(total_price), 0) as total_revenue
        FROM {settings.order_schema}.orders
    """)).mappings().one()

    status_stats = db.execute(text(f"""
        SELECT status, COUNT(*) as count
        FROM {settings.order_schema}.orders
        GROUP BY status
    """)).mappings().all()

    user_count = db.execute(text(f"""
        SELECT COUNT(*) as count FROM {settings.user_schema}.users WHERE role != 'admin'
    """)).mappings().one()

    product_count = db.execute(text(f"""
        SELECT COUNT(*) as count FROM {settings.product_schema}.products
    """)).mappings().one()

    top_products = db.execute(text(f"""
        SELECT p.name, SUM(oi.quantity) as sold_count
        FROM {settings.order_schema}.order_items oi
        JOIN {settings.product_schema}.products p ON oi.product_id = p.id
        GROUP BY p.name
        ORDER BY sold_count DESC
        LIMIT 5
    """)).mappings().all()

    recent_orders = db.execute(text(f"""
        SELECT o.id, o.total_price, o.status, o.created_at,
               u.email, u.name as user_name
        FROM {settings.order_schema}.orders o
        JOIN {settings.user_schema}.users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
        LIMIT 10
    """)).mappings().all()

    return {
        "total_orders": order_stats["total_orders"],
        "total_revenue": float(order_stats["total_revenue"]),
        "total_users": user_count["count"],
        "total_products": product_count["count"],
        "orders_by_status": [dict(r) for r in status_stats],
        "top_products": [dict(r) for r in top_products],
        "recent_orders": [dict(r) for r in recent_orders],
    }


@router.get("/orders")
def list_orders(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    q: str | None = None,
):
    conditions = []
    params: dict = {"size": size, "offset": (page - 1) * size}

    if status:
        conditions.append("o.status = :status")
        params["status"] = status
    if q:
        conditions.append("(u.name ILIKE :q OR u.email ILIKE :q)")
        params["q"] = f"%{q}%"

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    orders = db.execute(text(f"""
        SELECT o.id, o.total_price, o.status, o.created_at,
               u.email, u.name as user_name
        FROM {settings.order_schema}.orders o
        JOIN {settings.user_schema}.users u ON o.user_id = u.id
        {where}
        ORDER BY o.created_at DESC
        LIMIT :size OFFSET :offset
    """), params).mappings().all()

    count_params = {k: v for k, v in params.items() if k not in ("size", "offset")}
    total = db.execute(text(f"""
        SELECT COUNT(*) as count
        FROM {settings.order_schema}.orders o
        JOIN {settings.user_schema}.users u ON o.user_id = u.id
        {where}
    """), count_params).mappings().one()["count"]

    return {"items": [dict(o) for o in orders], "total": total, "page": page, "size": size}


@router.get("/users")
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    page: int = 1,
    size: int = 20,
    q: str | None = None,
):
    offset = (page - 1) * size
    params: dict = {"size": size, "offset": offset}
    search_clause = ""
    if q:
        search_clause = "AND (name ILIKE :q OR email ILIKE :q)"
        params["q"] = f"%{q}%"

    users = db.execute(text(f"""
        SELECT id, email, name, role, phone, created_at
        FROM {settings.user_schema}.users
        WHERE role != 'admin' {search_clause}
        ORDER BY created_at DESC
        LIMIT :size OFFSET :offset
    """), params).mappings().all()

    count_params = {"q": params["q"]} if q else {}
    total = db.execute(text(f"""
        SELECT COUNT(*) as count FROM {settings.user_schema}.users
        WHERE role != 'admin' {search_clause}
    """), count_params).mappings().one()["count"]

    return {"items": [dict(u) for u in users], "total": total, "page": page, "size": size}


@router.get("/products")
def list_products(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
    page: int = 1,
    size: int = 20,
    category: str | None = None,
    q: str | None = None,
):
    conditions = []
    params: dict = {"size": size, "offset": (page - 1) * size}

    if category:
        conditions.append("category = :category")
        params["category"] = category
    if q:
        conditions.append("(name ILIKE :q OR brand ILIKE :q)")
        params["q"] = f"%{q}%"

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    products = db.execute(text(f"""
        SELECT id, name, category, brand, price, stock_quantity, created_at
        FROM {settings.product_schema}.products
        {where}
        ORDER BY created_at DESC
        LIMIT :size OFFSET :offset
    """), params).mappings().all()

    count_params = {k: v for k, v in params.items() if k not in ("size", "offset")}
    total = db.execute(text(f"""
        SELECT COUNT(*) as count FROM {settings.product_schema}.products {where}
    """), count_params).mappings().one()["count"]

    return {"items": [dict(p) for p in products], "total": total, "page": page, "size": size}


@router.patch("/products/{product_id}/stock")
def update_stock(
    product_id: int,
    stock_quantity: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_admin)],
):
    db.execute(
        text(f"UPDATE {settings.product_schema}.products SET stock_quantity = :qty WHERE id = :id"),
        {"qty": stock_quantity, "id": product_id},
    )
    db.commit()
    return {"message": "stock updated"}
