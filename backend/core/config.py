from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Application Configuration
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")

    # Server Configuration
    SERVER_NAME: str = Field("ChatGPT Web App", env="SERVER_NAME")
    SERVER_HOST: str = Field("http://localhost", env="SERVER_HOST")
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )

    # Database Configuration
    POSTGRES_SERVER: str = Field("localhost", env="POSTGRES_SERVER")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")

    # Redis Configuration (for caching and sessions)
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")

    # File Upload Configuration
    MAX_UPLOAD_SIZE: int = Field(100 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 100MB
    UPLOAD_DIR: str = Field("./uploads", env="UPLOAD_DIR")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".json", ".zip", ".html"]
    )

    # Search Configuration
    DEFAULT_SEARCH_LIMIT: int = Field(50, env="DEFAULT_SEARCH_LIMIT")
    MAX_SEARCH_LIMIT: int = Field(500, env="MAX_SEARCH_LIMIT")
    SEARCH_TIMEOUT: int = Field(30, env="SEARCH_TIMEOUT")  # seconds

    # Embedding Configuration (optional)
    EMBEDDING_MODEL: str = Field("sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    EMBEDDING_DIMENSION: int = Field(384, env="EMBEDDING_DIMENSION")
    EMBEDDING_BATCH_SIZE: int = Field(32, env="EMBEDDING_BATCH_SIZE")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(60, env="RATE_LIMIT_WINDOW")  # seconds

    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")

    # External Services (optional)
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")  # For embeddings

    class Config:
        case_sensitive = True
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )


settings = Settings()




