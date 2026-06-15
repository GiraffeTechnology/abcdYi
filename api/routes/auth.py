import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.deps import get_db, get_current_user
from api.auth import verify_password, hash_password, create_access_token
from src.db.models.user import User, UserRole
from src.db.models.tenant import Tenant
from src.db.models.audit import AuditLog

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    slug = f"tenant-{uuid.uuid4().hex[:12]}"
    tenant = Tenant(name=body.email, slug=slug)
    db.add(tenant)
    await db.flush()
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    log = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action="REGISTER",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.add(log)
    await db.commit()
    return {"id": str(user.id), "email": user.email, "tenant_id": str(tenant.id)}


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(subject=str(user.id))
    log = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="LOGIN",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.add(log)
    await db.commit()
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "logged out"}


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == current_user.id)
    )
    roles = [r.role_name for r in result.scalars().all()]
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_platform_admin": current_user.is_platform_admin,
        "roles": roles,
    }
