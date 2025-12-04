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

    # Model parameters (see: promptingguide.ai/introduction/settings)
    ollama_max_tokens: int = 256  # Max tokens - lower = faster responses
    ollama_temperature: float = 0.3  # Creativity (0.0-1.0) - lower = more focused
    ollama_top_p: float = 0.9  # Nucleus sampling - balance diversity/quality
    ollama_repeat_penalty: float = 1.1  # Reduce repetition (1.0 = off)
    ollama_num_ctx: int = 2048  # Context window size

    # Response style preset (overrides individual params)
    # Options: "default", "brief", "detailed", "technical", "creative"
    response_style: str = "brief"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Admin
    admin_api_key: str = "change-me-in-production"

    # Feature flags
    feature_multi_agent: bool = False  # Enable multi-agent orchestration
    feature_external_providers: bool = False  # Enable Claude/OpenAI/Gemini providers

    # Encryption (for API keys)
    encryption_key: str | None = None  # Fernet key for encrypting stored API keys

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
