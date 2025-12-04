from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
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


settings = Settings()
