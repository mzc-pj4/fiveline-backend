from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.deps import CurrentUser, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
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
        SELECT COUNT(*) as count FROM {settings.user_schema}.users
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
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    where = f"WHERE o.status = :status" if status else ""
    offset = (page - 1) * size
    params: dict = {"size": size, "offset": offset}
    if status:
        params["status"] = status

    orders = db.execute(text(f"""
        SELECT o.id, o.total_price, o.status, o.created_at,
               u.email, u.name as user_name
        FROM {settings.order_schema}.orders o
        JOIN {settings.user_schema}.users u ON o.user_id = u.id
        {where}
        ORDER BY o.created_at DESC
        LIMIT :size OFFSET :offset
    """), params).mappings().all()

    count_params = {"status": status} if status else {}
    total = db.execute(text(f"""
        SELECT COUNT(*) as count FROM {settings.order_schema}.orders o {where}
    """), count_params).mappings().one()["count"]

    return {"items": [dict(o) for o in orders], "total": total, "page": page, "size": size}


@router.get("/users")
def list_users(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    offset = (page - 1) * size
    users = db.execute(text(f"""
        SELECT id, email, name, role, phone, created_at
        FROM {settings.user_schema}.users
        ORDER BY created_at DESC
        LIMIT :size OFFSET :offset
    """), {"size": size, "offset": offset}).mappings().all()

    total = db.execute(text(f"""
        SELECT COUNT(*) as count FROM {settings.user_schema}.users
    """)).mappings().one()["count"]

    return {"items": [dict(u) for u in users], "total": total, "page": page, "size": size}


@router.get("/products")
def list_products(
    page: int = 1,
    size: int = 20,
    category: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    where = "WHERE category = :category" if category else ""
    offset = (page - 1) * size
    params: dict = {"size": size, "offset": offset}
    if category:
        params["category"] = category

    products = db.execute(text(f"""
        SELECT id, name, category, brand, price, stock_quantity, created_at
        FROM {settings.product_schema}.products
        {where}
        ORDER BY created_at DESC
        LIMIT :size OFFSET :offset
    """), params).mappings().all()

    count_params = {"category": category} if category else {}
    total = db.execute(text(f"""
        SELECT COUNT(*) as count FROM {settings.product_schema}.products {where}
    """), count_params).mappings().one()["count"]

    return {"items": [dict(p) for p in products], "total": total, "page": page, "size": size}


@router.patch("/products/{product_id}/stock")
def update_stock(
    product_id: int,
    stock_quantity: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    db.execute(
        text(f"UPDATE {settings.product_schema}.products SET stock_quantity = :qty WHERE id = :id"),
        {"qty": stock_quantity, "id": product_id},
    )
    db.commit()
    return {"message": "stock updated"}
