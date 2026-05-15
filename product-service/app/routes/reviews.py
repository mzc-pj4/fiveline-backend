from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
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

    review = Review(
        product_id=product_id,
        user_id=current_user.user_id,
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
