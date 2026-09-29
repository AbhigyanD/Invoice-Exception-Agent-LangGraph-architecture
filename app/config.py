from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5544/invoice_agent"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    api_key: str = "dev-key"

    max_repair_attempts: int = 2
    auto_approve_max_amount: float = 1000.0
    min_confidence: float = 0.85

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""


settings = Settings()
