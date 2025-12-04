from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.core.auth import get_current_token
from app.core.logging import log_chat
from app.core.memory import (
    MemoryService,
    augment_system_prompt,
    format_memories_for_prompt,
)
from app.core.prompts import build_system_prompt
from app.core.rate_limit import limiter
from app.core.sessions import session_manager
from app.db.database import async_session
from app.db.models import AppToken
from app.providers.ollama import ollama_provider

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context: dict | None = None  # Page/app context from frontend
    style: str | None = None  # Response style override


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    token: AppToken = Depends(get_current_token),
):
    session = session_manager.get_or_create_session(
        session_id=body.session_id,
        app_token_id=token.id,
        context=body.context,
    )

    history = [{"role": m.role, "content": m.content} for m in session.messages]
    system_prompt = build_system_prompt(session.context, body.style)

    # Recall relevant memories and augment prompt
    if settings.feature_memory:
        async with async_session() as db:
            memory_service = MemoryService(db)
            memories = await memory_service.recall(
                app_token_id=token.id,
                query=body.message,
                limit=settings.memory_recall_limit,
                min_similarity=settings.memory_min_similarity,
            )
            if memories:
                memory_context = format_memories_for_prompt(memories)
                system_prompt = augment_system_prompt(system_prompt, memory_context)

    log_chat(session.id, len(body.message), "ollama")

    response_text = await ollama_provider.generate(
        prompt=body.message,
        system_prompt=system_prompt,
        messages=history if history else None,
    )

    session_manager.add_message(session.id, "user", body.message)
    session_manager.add_message(session.id, "assistant", response_text)

    return ChatResponse(response=response_text, session_id=session.id)


@router.post("/chat/stream")
@limiter.limit("60/minute")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    token: AppToken = Depends(get_current_token),
):
    session = session_manager.get_or_create_session(
        session_id=body.session_id,
        app_token_id=token.id,
        context=body.context,
    )

    history = [{"role": m.role, "content": m.content} for m in session.messages]
    system_prompt = build_system_prompt(session.context, body.style)

    # Recall relevant memories and augment prompt
    if settings.feature_memory:
        async with async_session() as db:
            memory_service = MemoryService(db)
            memories = await memory_service.recall(
                app_token_id=token.id,
                query=body.message,
                limit=settings.memory_recall_limit,
                min_similarity=settings.memory_min_similarity,
            )
            if memories:
                memory_context = format_memories_for_prompt(memories)
                system_prompt = augment_system_prompt(system_prompt, memory_context)

    log_chat(session.id, len(body.message), "ollama")

    async def event_generator():
        full_response = ""
        async for chunk in ollama_provider.generate_stream(
            prompt=body.message,
            system_prompt=system_prompt,
            messages=history if history else None,
        ):
            full_response += chunk
            yield {"event": "message", "data": chunk}

        session_manager.add_message(session.id, "user", body.message)
        session_manager.add_message(session.id, "assistant", full_response)

        yield {"event": "done", "data": session.id}

    return EventSourceResponse(event_generator())
