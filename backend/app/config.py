"""
Central application configuration.

All values are read from environment variables (see .env.example). Nothing
sensitive is hard-coded. If AI_API_KEY is not set, the application
automatically runs in "deterministic fallback" mode for every AI-adjacent
feature (natural language parsing, the AI assistant, and insight narration).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./finance_agent.db"

    ai_api_key: str = ""
    ai_model: str = "claude-3-5-haiku-latest"
    ai_provider: str = "anthropic"

    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    seed_demo_data: bool = True

    default_currency: str = "INR"
    default_currency_symbol: str = "\u20b9"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
