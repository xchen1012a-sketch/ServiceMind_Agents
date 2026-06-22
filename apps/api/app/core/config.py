from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "ServiceMind API"
    app_version: str = "0.1.0"
    environment: str = "local"
    cors_origins: list[str] = [
        "http://localhost:15174",
        "http://127.0.0.1:15174",
    ]
    database_url: str = (
        "postgresql+psycopg://servicemind:servicemind@localhost:5432/servicemind"
        "?connect_timeout=5"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SERVICEMIND_",
        extra="ignore",
    )


settings = Settings()
