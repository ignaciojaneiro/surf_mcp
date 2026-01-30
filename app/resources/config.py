"""Configuration settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Windy API
    windy_api_key: str = ""
    windy_api_url: str = "https://api.windy.com/api/point-forecast/v2"

    # HTTP Client
    http_timeout: int = 30
    max_retries: int = 3

    # Server
    port: int = 8000
    log_level: str = "INFO"

    # Environment
    environment: str = "development"

    # MCP Transport (http/stdio)
    mcp_transport: str = "http"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
