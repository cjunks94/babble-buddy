from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (Railway provides DATABASE_URL without +asyncpg)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/babble_buddy"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Admin
    admin_api_key: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to asyncpg format for SQLAlchemy async."""
        url = self.database_url
        # Railway uses postgresql://, we need postgresql+asyncpg://
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
