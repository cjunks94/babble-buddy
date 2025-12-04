from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import AppToken

security = HTTPBearer()


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AppToken:
    token = credentials.credentials

    result = await db.execute(select(AppToken).where(AppToken.token == token, AppToken.is_active))
    app_token = result.scalar_one_or_none()

    if not app_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive token",
        )

    await db.execute(
        update(AppToken).where(AppToken.id == app_token.id).values(last_used_at=datetime.utcnow())
    )
    await db.commit()

    return app_token


async def verify_admin_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> bool:
    if credentials.credentials != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )
    return True
