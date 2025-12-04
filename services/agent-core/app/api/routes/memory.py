"""Memory management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.core.auth import get_current_token
from app.core.memory import MemoryService, format_memories_for_prompt
from app.db.database import async_session
from app.db.models import AppToken, MemoryType

router = APIRouter()


class StoreMemoryRequest(BaseModel):
    content: str
    memory_type: str = "fact"  # fact, preference, summary
    session_id: str | None = None


class StoreMemoryResponse(BaseModel):
    id: int
    content: str
    memory_type: str


class SearchMemoryRequest(BaseModel):
    query: str
    limit: int = 5


class MemoryResult(BaseModel):
    id: int
    content: str
    memory_type: str
    similarity: float


class SearchMemoryResponse(BaseModel):
    memories: list[MemoryResult]
    formatted: str


@router.post("/memory", response_model=StoreMemoryResponse)
async def store_memory(
    body: StoreMemoryRequest,
    token: AppToken = Depends(get_current_token),
):
    """Store a new memory (fact, preference, or summary)."""
    if not settings.feature_memory:
        raise HTTPException(status_code=403, detail="Memory feature is disabled")

    # Validate memory type
    try:
        mem_type = MemoryType(body.memory_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid memory_type. Must be one of: {[t.value for t in MemoryType]}",
        )

    async with async_session() as db:
        memory_service = MemoryService(db)
        memory = await memory_service.store(
            app_token_id=token.id,
            session_id=body.session_id,
            content=body.content,
            memory_type=mem_type,
        )

        return StoreMemoryResponse(
            id=memory.id,
            content=memory.content,
            memory_type=memory.memory_type.value,
        )


@router.post("/memory/search", response_model=SearchMemoryResponse)
async def search_memories(
    body: SearchMemoryRequest,
    token: AppToken = Depends(get_current_token),
):
    """Search memories by semantic similarity."""
    if not settings.feature_memory:
        raise HTTPException(status_code=403, detail="Memory feature is disabled")

    async with async_session() as db:
        memory_service = MemoryService(db)
        memories = await memory_service.recall(
            app_token_id=token.id,
            query=body.query,
            limit=body.limit,
            min_similarity=settings.memory_min_similarity,
        )

        results = [
            MemoryResult(
                id=m.id,
                content=m.content,
                memory_type=m.memory_type.value,
                similarity=m.similarity,
            )
            for m in memories
        ]

        return SearchMemoryResponse(
            memories=results,
            formatted=format_memories_for_prompt(memories),
        )


@router.delete("/memory")
async def clear_memories(
    session_id: str | None = None,
    token: AppToken = Depends(get_current_token),
):
    """Clear all memories for this app token, optionally filtered by session."""
    if not settings.feature_memory:
        raise HTTPException(status_code=403, detail="Memory feature is disabled")

    async with async_session() as db:
        memory_service = MemoryService(db)
        count = await memory_service.clear(
            app_token_id=token.id,
            session_id=session_id,
        )

        return {"deleted": count}
