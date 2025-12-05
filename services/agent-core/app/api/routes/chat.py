from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.core.auth import get_current_token
from app.core.logging import log_chat, logger
from app.core.memory import (
    MemoryService,
    augment_system_prompt,
    format_combined_memories_for_prompt,
    format_memories_for_prompt,
)
from app.core.prompts import build_system_prompt
from app.core.rate_limit import limiter
from app.core.sessions import session_manager
from app.db.database import async_session, pgvector_available
from app.db.models import AppToken, ConversationTurn
from app.providers.ollama import ollama_provider

router = APIRouter()


async def store_conversation_turn(
    app_token_id: int,
    session_id: str,
    user_message: str,
    assistant_message: str,
    context: dict | None = None,
    application_group: str | None = None,
) -> None:
    """Store a conversation turn for later memory extraction."""
    if not settings.memory_extraction_enabled or not pgvector_available:
        return

    try:
        async with async_session() as db:
            turn = ConversationTurn(
                app_token_id=app_token_id,
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                context=context,
                application_group=application_group or context.get("app") if context else None,
            )
            db.add(turn)
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to store conversation turn: {e}")


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

    # Recall relevant memories and augment prompt (if pgvector available)
    if settings.feature_memory and pgvector_available:
        try:
            async with async_session() as db:
                memory_service = MemoryService(db)
                application_group = body.context.get("app") if body.context else None

                # Use combined recall for both basic and structured memories
                combined = await memory_service.recall_combined(
                    app_token_id=token.id,
                    query=body.message,
                    limit=settings.memory_recall_limit,
                    min_similarity=settings.memory_min_similarity,
                    application_group=application_group,
                )

                memory_context = format_combined_memories_for_prompt(combined)
                if memory_context:
                    system_prompt = augment_system_prompt(system_prompt, memory_context)
        except Exception:
            pass  # Memory recall failed, continue without it

    log_chat(session.id, len(body.message), "ollama")

    response_text = await ollama_provider.generate(
        prompt=body.message,
        system_prompt=system_prompt,
        messages=history if history else None,
    )

    session_manager.add_message(session.id, "user", body.message)
    session_manager.add_message(session.id, "assistant", response_text)

    # Store turn for memory extraction
    await store_conversation_turn(
        app_token_id=token.id,
        session_id=session.id,
        user_message=body.message,
        assistant_message=response_text,
        context=body.context,
    )

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

    # Recall relevant memories and augment prompt (if pgvector available)
    if settings.feature_memory and pgvector_available:
        try:
            async with async_session() as db:
                memory_service = MemoryService(db)
                application_group = body.context.get("app") if body.context else None

                # Use combined recall for both basic and structured memories
                combined = await memory_service.recall_combined(
                    app_token_id=token.id,
                    query=body.message,
                    limit=settings.memory_recall_limit,
                    min_similarity=settings.memory_min_similarity,
                    application_group=application_group,
                )

                memory_context = format_combined_memories_for_prompt(combined)
                if memory_context:
                    system_prompt = augment_system_prompt(system_prompt, memory_context)
        except Exception:
            pass  # Memory recall failed, continue without it

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

        # Store turn for memory extraction
        await store_conversation_turn(
            app_token_id=token.id,
            session_id=session.id,
            user_message=body.message,
            assistant_message=full_response,
            context=body.context,
        )

        yield {"event": "done", "data": session.id}

    return EventSourceResponse(event_generator())
