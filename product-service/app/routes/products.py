import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.cache import get_redis, get_redis_read
from app.core.logging import log_service_event
from app.db.session import get_db
from app.models.product import Product
from app.models.review import Review
from app.schemas.product import ProductCreate, ProductList, ProductListItem, ProductPublic

router = APIRouter(prefix="/api/products", tags=["products"])

CACHE_TTL_LIST = 300
CACHE_TTL_DETAIL = 600
CACHE_TTL_BRANDS = 1800


def _make_key(prefix: str, **kwargs) -> str:
    raw = json.dumps(kwargs, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"


@router.get("", response_model=ProductList)
def list_products(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=100, description="상품명/설명 검색"),
    category: str | None = Query(default=None, max_length=50),
    brand: str | None = Query(default=None, max_length=100),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: str | None = Query(default="newest", pattern="^(newest|price_asc|price_desc)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> ProductList:
    cache_key = _make_key(
        "products:list",
        q=q, category=category, brand=brand,
        min_price=min_price, max_price=max_price,
        sort=sort, page=page, size=size,
    )
    r_r = get_redis_read()
    if r_r:
        try:
            cached = r_r.get(cache_key)
            if cached:
                return ProductList.model_validate_json(cached)
        except Exception:
            pass

    stmt = select(Product)
    if q:
        stmt = stmt.where(
            Product.name.ilike(f"%{q}%") | Product.brand.ilike(f"%{q}%")
        )
    if category:
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)

    if sort == "price_asc":
        stmt = stmt.order_by(asc(Product.price))
    elif sort == "price_desc":
        stmt = stmt.order_by(desc(Product.price))
    else:
        stmt = stmt.order_by(desc(Product.created_at))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    offset = (page - 1) * size
    rows = db.execute(stmt.limit(size).offset(offset)).scalars().all()

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
                id=p.id, name=p.name, category=p.category, brand=p.brand,
                price=p.price, original_price=p.original_price,
                stock_quantity=p.stock_quantity, image_url=p.image_url,
                average_rating=avg, review_count=cnt,
            )
        )

    log_service_event(
        "PRODUCT_SEARCH" if (q or category) else "PRODUCT_LIST_VIEW",
        q=q, category=category, result_count=len(items), total=total,
    )
    result = ProductList(items=items, total=total, page=page, size=size)
    r_w = get_redis()
    if r_w:
        try:
            r_w.setex(cache_key, CACHE_TTL_LIST, result.model_dump_json())
        except Exception:
            pass
    return result


_GENDER_SUFFIXES = (" 우먼", " 맨", " 여성", " 남성", " women", " men")

@router.get("/brands", response_model=list[str])
def list_brands(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
) -> list[str]:
    cache_key = _make_key("products:brands", limit=limit)
    r_r = get_redis_read()
    if r_r:
        try:
            cached = r_r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    rows = db.execute(
        select(Product.brand, func.count(Product.id).label("cnt"))
        .where(Product.brand.isnot(None), Product.brand != "")
        .group_by(Product.brand)
        .order_by(desc("cnt"))
        .limit(limit * 3)  # 필터링 여유분
    ).all()
    all_brands = [row.brand for row in rows if row.brand]

    # 베이스 브랜드 목록 (성별 접미사 제거)
    def base(b: str) -> str:
        lower = b.lower()
        for suf in _GENDER_SUFFIXES:
            if lower.endswith(suf.lower()):
                return b[: len(b) - len(suf)].strip()
        return b

    standalone = {b for b in all_brands if base(b) == b}

    result: list[str] = []
    for b in all_brands:
        b_base = base(b)
        if b_base == b or b_base not in standalone:
            result.append(b)
        if len(result) >= limit:
            break

    r_w = get_redis()
    if r_w:
        try:
            r_w.setex(cache_key, CACHE_TTL_BRANDS, json.dumps(result))
        except Exception:
            pass
    return result


@router.get("/{product_id}", response_model=ProductPublic)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductPublic:
    cache_key = f"products:detail:{product_id}"
    r_r = get_redis_read()
    if r_r:
        try:
            cached = r_r.get(cache_key)
            if cached:
                return ProductPublic.model_validate_json(cached)
        except Exception:
            pass

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    log_service_event("PRODUCT_VIEW", product_id=product_id, category=product.category)
    result = ProductPublic.model_validate(product)
    r_w = get_redis()
    if r_w:
        try:
            r_w.setex(cache_key, CACHE_TTL_DETAIL, result.model_dump_json())
        except Exception:
            pass
    return result


@router.post("", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductPublic:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductPublic.model_validate(product)
