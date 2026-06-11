from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.logging import log_service_event
from app.db.session import get_db
from app.deps import CurrentUser, get_current_user
from app.models.product import Product
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewPublic

router = APIRouter(prefix="/api/products/{product_id}/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewPublic])
def list_reviews(product_id: int, db: Session = Depends(get_db)) -> list[ReviewPublic]:
    rows = db.execute(
        select(Review).where(Review.product_id == product_id).order_by(Review.id.desc())
    ).scalars().all()
    return [ReviewPublic.model_validate(r) for r in rows]


def _has_purchased(db: Session, user_id: int, product_id: int) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM order_schema.orders o"
            " JOIN order_schema.order_items oi ON oi.order_id = o.id"
            " WHERE o.user_id = :user_id"
            "   AND oi.product_id = :product_id"
            "   AND o.status = 'SUCCESS'"
            " LIMIT 1"
        ),
        {"user_id": user_id, "product_id": product_id},
    ).fetchone()
    return row is not None


def _already_reviewed(db: Session, user_id: int, product_id: int) -> bool:
    row = db.execute(
        select(Review.id)
        .where(Review.user_id == user_id, Review.product_id == product_id)
        .limit(1)
    ).fetchone()
    return row is not None


@router.post("", response_model=ReviewPublic, status_code=status.HTTP_201_CREATED)
def create_review(
    product_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ReviewPublic:
    product = db.get(Product, product_id)
    if product is None:
        log_service_event("REVIEW_FAILED", product_id=product_id, reason="PRODUCT_NOT_FOUND")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")

    if not _has_purchased(db, current_user.user_id, product_id):
        log_service_event("REVIEW_FAILED", product_id=product_id, user_id=current_user.user_id, reason="NOT_PURCHASED")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "구매한 상품에만 리뷰를 작성할 수 있습니다")

    if _already_reviewed(db, current_user.user_id, product_id):
        log_service_event("REVIEW_FAILED", product_id=product_id, user_id=current_user.user_id, reason="DUPLICATE_REVIEW")
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 해당 상품에 리뷰를 작성하셨습니다")

    review = Review(
        product_id=product_id,
        user_id=current_user.user_id,
        reviewer_name=current_user.name or None,
        rating=payload.rating,
        content=payload.content,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    log_service_event(
        "REVIEW_CREATED",
        review_id=review.id,
        product_id=product_id,
        user_id=current_user.user_id,
        rating=payload.rating,
    )
    return ReviewPublic.model_validate(review)
