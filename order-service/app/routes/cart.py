from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.product_client import ProductClientError, ProductNotFound, get_product
from app.core.logging import log_service_event
from app.db.session import get_db
from app.deps import CurrentUser, get_current_user
from app.models.cart import CartItem
from app.schemas.cart import CartItemCreate, CartItemPublic, CartItemUpdate, CartView

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _to_public(item: CartItem) -> CartItemPublic:
    line_total = (item.product_price or Decimal("0")) * item.quantity
    return CartItemPublic(
        id=item.id,
        product_id=item.product_id,
        quantity=item.quantity,
        created_at=item.created_at,
        product_name=item.product_name,
        product_price=item.product_price,
        line_total=line_total,
    )


@router.post("/items", response_model=CartItemPublic, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartItemPublic:
    try:
        product = get_product(payload.product_id)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    except ProductClientError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    existing = db.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.user_id,
            CartItem.product_id == payload.product_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.quantity += payload.quantity
        existing.product_name = product.name
        existing.product_price = product.price
        item = existing
    else:
        item = CartItem(
            user_id=current_user.user_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            product_name=product.name,
            product_price=product.price,
        )
        db.add(item)
    db.commit()
    db.refresh(item)

    log_service_event(
        "CART_ITEM_ADDED",
        user_id=current_user.user_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        cart_item_id=item.id,
    )
    return _to_public(item)


@router.get("", response_model=CartView)
def view_cart(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartView:
    rows = db.execute(
        select(CartItem).where(CartItem.user_id == current_user.user_id).order_by(CartItem.id)
    ).scalars().all()

    items = [_to_public(row) for row in rows]
    total = sum((row.product_price or Decimal("0")) * row.quantity for row in rows)

    log_service_event("CART_VIEWED", user_id=current_user.user_id, item_count=len(items))
    return CartView(items=items, total_price=total)


@router.patch("/items/{cart_item_id}", response_model=CartItemPublic)
def update_cart_item(
    cart_item_id: int,
    payload: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartItemPublic:
    item = db.get(CartItem, cart_item_id)
    if item is None or item.user_id != current_user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cart item not found")
    item.quantity = payload.quantity
    db.commit()
    db.refresh(item)

    log_service_event(
        "CART_ITEM_UPDATED",
        cart_item_id=item.id, user_id=current_user.user_id, quantity=item.quantity,
    )
    return _to_public(item)


@router.delete("/items/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(
    cart_item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    item = db.get(CartItem, cart_item_id)
    if item is None or item.user_id != current_user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cart item not found")
    db.delete(item)
    db.commit()
    log_service_event(
        "CART_ITEM_REMOVED", cart_item_id=cart_item_id, user_id=current_user.user_id,
    )
