from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database - supports both URL and individual params
    database_url: str | None = None
    pghost: str = "localhost"
    pgport: str = "5432"
    pguser: str = "postgres"
    pgpassword: str = "postgres"
    pgdatabase: str = "railway"

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
        """Build async database URL from components or convert provided URL."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        # Build from individual components (more reliable)
        password = quote_plus(self.pgpassword)
        return f"postgresql+asyncpg://{self.pguser}:{password}@{self.pghost}:{self.pgport}/{self.pgdatabase}"


settings = Settings()
