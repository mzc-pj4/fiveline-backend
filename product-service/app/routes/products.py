from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import log_service_event
from app.db.session import get_db
from app.models.product import Product
from app.models.review import Review
from app.schemas.product import ProductCreate, ProductList, ProductListItem, ProductPublic

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductList)
def list_products(
    db: Session = Depends(get_db),
    keyword: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductList:
    stmt = select(Product)
    if keyword:
        stmt = stmt.where(Product.name.ilike(f"%{keyword}%"))
    if category:
        stmt = stmt.where(Product.category == category)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Product.id.desc()).limit(limit).offset(offset)).scalars().all()

    product_ids = [p.id for p in rows]
    review_agg: dict[int, tuple[float | None, int]] = {}
    if product_ids:
        agg_rows = db.execute(
            select(Review.product_id, func.avg(Review.rating), func.count(Review.id))
            .where(Review.product_id.in_(product_ids))
            .group_by(Review.product_id)
        ).all()
        for pid, avg, cnt in agg_rows:
            review_agg[pid] = (float(avg) if avg is not None else None, int(cnt))

    items = []
    for p in rows:
        avg, cnt = review_agg.get(p.id, (None, 0))
        items.append(
            ProductListItem(
                id=p.id, name=p.name, category=p.category, price=p.price,
                stock_quantity=p.stock_quantity, image_url=p.image_url,
                average_rating=avg, review_count=cnt,
            )
        )

    log_service_event(
        "PRODUCT_SEARCH" if (keyword or category) else "PRODUCT_LIST_VIEW",
        keyword=keyword, category=category, result_count=len(items), total=total,
    )
    return ProductList(items=items, total=total)


@router.get("/{product_id}", response_model=ProductPublic)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductPublic:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    log_service_event("PRODUCT_VIEW", product_id=product_id, category=product.category)
    return ProductPublic.model_validate(product)


@router.post("", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductPublic:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductPublic.model_validate(product)
