from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import chat, health, memory, tokens
from app.config import settings
from app.core.logging import log_startup, logger
from app.core.rate_limit import limiter
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_startup(
        {
            "ollama_host": settings.ollama_host,
            "ollama_model": settings.ollama_model,
            "response_style": settings.response_style,
            "rate_limit": f"{settings.rate_limit_per_minute}/min",
            "debug": settings.debug,
        }
    )
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Babble Buddy Agent Core",
    description="Centralized AI chatbot backend for embeddable widgets",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(memory.router, prefix="/api/v1", tags=["Memory"])
app.include_router(tokens.router, prefix="/api/v1/admin", tags=["Admin"])

# Serve widget bundle as static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/widget", StaticFiles(directory=static_dir), name="static")
