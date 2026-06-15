from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.permissions.engine import Permission, has_permission
from api.deps import get_current_user_id, get_db
from src.db.models.user import UserRole


def require_permission(permission: Permission):
    async def checker(
        current_user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
    ):
        result = await db.execute(
            select(UserRole).where(UserRole.user_id == current_user_id)
        )
        user_roles = [r.role_name for r in result.scalars().all()]
        if not has_permission(user_roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    return checker
