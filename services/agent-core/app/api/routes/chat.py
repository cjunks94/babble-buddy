from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.core.auth import get_current_token
from app.core.rate_limit import limiter
from app.core.sessions import session_manager
from app.db.models import AppToken
from app.providers.ollama import ollama_provider

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context: dict | None = None


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

    system_prompt = _build_system_prompt(session.context)

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
    system_prompt = _build_system_prompt(session.context)

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


def _build_system_prompt(context: dict | None) -> str:
    base_prompt = """You are a helpful AI assistant. Be concise and direct.
Keep responses brief unless asked for detail. Use markdown sparingly:
- Use `code` for inline code
- Use ```lang for code blocks (always close with ```)
- Use **bold** for emphasis
Avoid long explanations or numbered lists unless specifically asked."""

    if not context:
        return base_prompt

    app_name = context.get("app", "")
    if app_name:
        base_prompt = f"You are a helpful AI assistant for {app_name}. " + base_prompt.split(". ", 1)[1]

    if "schema" in context:
        schema_info = context["schema"]
        if isinstance(schema_info, list):
            base_prompt += f" Available tables: {', '.join(schema_info)}."
        elif isinstance(schema_info, str):
            base_prompt += f" {schema_info}"

    if "instructions" in context:
        base_prompt += f" {context['instructions']}"

    return base_prompt
