from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Integer, String, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.config import settings
from app.core.security import issue_access_token
from app.db.base import Base
from app.db.session import get_db

router = APIRouter(prefix="/api/auth/admin", tags=["admin-auth"])


class AdminUser(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": settings.user_schema}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    employee_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)


class AdminRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    employee_id: str = Field(min_length=1, max_length=50)


class AdminLoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    employee_id: str = Field(min_length=1, max_length=50)


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    role: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def admin_register(payload: AdminRegisterRequest, db: Annotated[Session, Depends(get_db)]) -> AdminTokenResponse:
    existing = db.execute(
        select(AdminUser).where(AdminUser.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 등록된 사원번호입니다")

    db.execute(text(f"""
        INSERT INTO {settings.user_schema}.users (email, password_hash, name, role, employee_id)
        VALUES (:email, :pw, :name, 'admin', :eid)
    """), {
        "email": f"{payload.employee_id}@admin.fiveline",
        "pw": payload.employee_id,
        "name": payload.name,
        "eid": payload.employee_id,
    })
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 등록된 사원번호입니다")

    user = db.execute(
        select(AdminUser).where(AdminUser.employee_id == payload.employee_id)
    ).scalar_one()

    token = issue_access_token(subject=str(user.id), extra_claims={"role": "admin", "name": user.name})
    return AdminTokenResponse(access_token=token, name=user.name, role="admin")


@router.post("/login")
def admin_login(payload: AdminLoginRequest, db: Annotated[Session, Depends(get_db)]) -> AdminTokenResponse:
    user = db.execute(
        select(AdminUser).where(
            AdminUser.employee_id == payload.employee_id,
            AdminUser.name == payload.name,
            AdminUser.role == "admin",
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이름 또는 관리자번호가 올바르지 않습니다")

    token = issue_access_token(subject=str(user.id), extra_claims={"role": "admin", "name": user.name})
    return AdminTokenResponse(access_token=token, name=user.name, role="admin")
