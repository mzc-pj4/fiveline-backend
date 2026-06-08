from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import log_service_event
from app.core.security import hash_password, issue_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, SignupRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        role="customer",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    db.refresh(user)

    log_service_event("USER_SIGNUP", user_id=user.id, email=user.email)

    token = issue_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        log_service_event("USER_LOGIN_FAILED", email=payload.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    log_service_event("USER_LOGIN", user_id=user.id, email=user.email)

    token = issue_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))
