"""Admin endpoints for memory extraction management."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import verify_admin_key
from app.core.memory_extractor import MemoryExtractor
from app.db.database import get_db

router = APIRouter()


class ExtractionRequest(BaseModel):
    """Request to trigger batch extraction."""

    app_token_id: int | None = None
    application_group: str | None = None
    limit: int | None = None


class ExtractionStatsResponse(BaseModel):
    """Response with extraction statistics."""

    total: int
    completed: int
    skipped: int
    failed: int
    memories_created: int


class PendingCountResponse(BaseModel):
    """Response with pending turn count."""

    pending_count: int
    extraction_enabled: bool


@router.get("/extraction/status", response_model=PendingCountResponse)
async def get_extraction_status(
    app_token_id: int | None = None,
    application_group: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    """Get the status of memory extraction.

    Returns count of pending turns awaiting extraction.
    """
    extractor = MemoryExtractor(db)
    count = await extractor.get_pending_count(
        app_token_id=app_token_id,
        application_group=application_group,
    )

    return PendingCountResponse(
        pending_count=count,
        extraction_enabled=settings.memory_extraction_enabled,
    )


@router.post("/extraction/run", response_model=ExtractionStatsResponse)
async def run_extraction(
    body: ExtractionRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    """Trigger batch memory extraction.

    Processes pending conversation turns and extracts structured memories.
    This is meant to be called periodically by an admin or scheduler.
    """
    if not settings.memory_extraction_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Memory extraction is disabled. Set MEMORY_EXTRACTION_ENABLED=true",
        )

    extractor = MemoryExtractor(db)

    try:
        stats = await extractor.process_batch(
            app_token_id=body.app_token_id,
            application_group=body.application_group,
            limit=body.limit,
        )

        return ExtractionStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}",
        )
