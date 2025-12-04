from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.db.database import get_db
from app.db.models import AppToken

router = APIRouter()


class TokenCreate(BaseModel):
    name: str
    description: str | None = None


class TokenResponse(BaseModel):
    id: int
    token: str
    name: str
    description: str | None
    is_active: bool
    created_at: str
    last_used_at: str | None

    class Config:
        from_attributes = True


class TokenListResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: str
    last_used_at: str | None

    class Config:
        from_attributes = True


@router.post("/tokens", response_model=TokenResponse)
async def create_token(
    body: TokenCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    token = AppToken(
        token=AppToken.generate_token(),
        name=body.name,
        description=body.description,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)

    return TokenResponse(
        id=token.id,
        token=token.token,
        name=token.name,
        description=token.description,
        is_active=token.is_active,
        created_at=token.created_at.isoformat(),
        last_used_at=token.last_used_at.isoformat() if token.last_used_at else None,
    )


@router.get("/tokens", response_model=list[TokenListResponse])
async def list_tokens(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    result = await db.execute(select(AppToken).order_by(AppToken.created_at.desc()))
    tokens = result.scalars().all()

    return [
        TokenListResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            is_active=t.is_active,
            created_at=t.created_at.isoformat(),
            last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
        )
        for t in tokens
    ]


@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    result = await db.execute(select(AppToken).where(AppToken.id == token_id))
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    token.is_active = False
    await db.commit()

    return {"message": "Token revoked successfully"}
