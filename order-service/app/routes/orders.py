import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.clients.product_client import ProductClientError, ProductNotFound, get_product
from app.core.logging import log_service_event
from app.db.session import get_db
from app.deps import CurrentUser, get_current_user
from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.schemas.order import OrderPublic
from app.services.failure_sim import maybe_delay, maybe_fail

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/from-cart", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
def create_order_from_cart(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderPublic:
    start = time.perf_counter()
    slept_ms = maybe_delay()

    cart_rows = db.execute(
        select(CartItem).where(CartItem.user_id == current_user.user_id)
    ).scalars().all()
    if not cart_rows:
        log_service_event(
            "ORDER_FAILED",
            user_id=current_user.user_id,
            error_code="EMPTY_CART",
            response_time_ms=int((time.perf_counter() - start) * 1000),
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cart is empty")

    error_code = maybe_fail()

    order = Order(user_id=current_user.user_id, total_price=Decimal("0"), status="PENDING")
    db.add(order)
    db.flush()

    # 상품 정보를 병렬로 조회 (N+1 순차 → ThreadPoolExecutor 병렬)
    def fetch_product(row: CartItem):
        try:
            return row, get_product(row.product_id), None
        except ProductNotFound:
            return row, None, "PRODUCT_NOT_FOUND"
        except ProductClientError:
            return row, None, "PRODUCT_SERVICE_UNREACHABLE"

    product_results: dict[int, tuple] = {}
    with ThreadPoolExecutor(max_workers=min(len(cart_rows), 10)) as pool:
        futures = {pool.submit(fetch_product, row): row for row in cart_rows}
        for future in as_completed(futures):
            row, product, err = future.result()
            product_results[row.product_id] = (product, err)

    total = Decimal("0")
    for row in cart_rows:
        product, fetch_err = product_results.get(row.product_id, (None, "PRODUCT_SERVICE_UNREACHABLE"))
        if fetch_err:
            error_code = error_code or fetch_err
            continue
        order_item = OrderItem(
            order_id=order.id,
            product_id=row.product_id,
            product_name=product.name,
            quantity=row.quantity,
            price=product.price,
        )
        db.add(order_item)
        total += product.price * row.quantity

    order.total_price = total
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    order.response_time_ms = elapsed_ms

    log_service_event(
        "ORDER_FROM_CART",
        order_id=order.id,
        user_id=current_user.user_id,
        item_count=len(cart_rows),
        simulated_delay_ms=slept_ms,
    )

    if error_code:
        order.status = "FAILED"
        order.error_code = error_code
        db.commit()
        log_service_event(
            "ORDER_FAILED",
            order_id=order.id,
            user_id=current_user.user_id,
            error_code=error_code,
            response_time_ms=elapsed_ms,
            total_price=str(total),
        )
        db.refresh(order)
        full = db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
        ).scalar_one()
        return OrderPublic.model_validate(full)

    order.status = "SUCCESS"
    for row in cart_rows:
        db.delete(row)
    db.commit()
    db.refresh(order)
    full = db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    ).scalar_one()

    log_service_event(
        "ORDER_SUCCESS",
        order_id=order.id,
        user_id=current_user.user_id,
        total_price=str(total),
        response_time_ms=elapsed_ms,
    )
    return OrderPublic.model_validate(full)


@router.get("/me", response_model=list[OrderPublic])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[OrderPublic]:
    rows = db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == current_user.user_id)
        .order_by(Order.id.desc())
    ).scalars().all()
    return [OrderPublic.model_validate(r) for r in rows]
