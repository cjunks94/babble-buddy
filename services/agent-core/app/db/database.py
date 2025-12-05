from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.logging import logger

engine = create_async_engine(settings.async_database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Track if pgvector is available
pgvector_available = False


async def init_db():
    """Initialize database, checking for pgvector support."""
    global pgvector_available
    from app.db.models import Base, Memory, StructuredMemory

    async with engine.begin() as conn:
        # Check if pgvector extension is available
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            pgvector_available = True
            logger.info("pgvector extension enabled - memory feature available")
        except Exception as e:
            pgvector_available = False
            logger.warning(f"pgvector not available - memory feature disabled: {e}")
            # Remove tables with vector columns from metadata
            for model in [Memory, StructuredMemory]:
                if model.__table__.name in Base.metadata.tables:
                    Base.metadata.remove(model.__table__)

        # Create all tables (ConversationTurn works without pgvector)
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
