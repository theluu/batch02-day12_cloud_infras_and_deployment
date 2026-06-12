"""
Config tập trung — 12-Factor: toàn bộ config từ environment variables.
Không có secret nào trong code. Fail fast nếu thiếu config bắt buộc.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"

    # App
    app_name: str = "My Production Agent"
    app_version: str = "1.0.0"

    # State / Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    # Một key đơn: AGENT_API_KEY=abc → user "default"
    # Nhiều key:   AGENT_API_KEYS=key1:alice,key2:bob
    agent_api_key: str = ""
    agent_api_keys: str = ""

    # Rate limiting & cost guard
    rate_limit_per_minute: int = 10
    monthly_budget_usd: float = 10.0

    # LLM (để trống → dùng mock)
    openai_api_key: str = ""
    llm_model: str = "mock-llm"

    class Config:
        env_file = ".env"

    def api_key_map(self) -> dict[str, str]:
        """Map api_key → user_id."""
        keys: dict[str, str] = {}
        if self.agent_api_key:
            keys[self.agent_api_key] = "default"
        for pair in self.agent_api_keys.split(","):
            if ":" in pair:
                key, user = pair.split(":", 1)
                keys[key.strip()] = user.strip()
        return keys


settings = Settings()

if settings.environment == "production" and not settings.api_key_map():
    raise ValueError("AGENT_API_KEY (hoặc AGENT_API_KEYS) bắt buộc khi ENVIRONMENT=production")
