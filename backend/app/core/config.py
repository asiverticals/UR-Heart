from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urheart"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "ur-heart-sanctuary-local-secret-key-32b"
    PROJECT_NAME: str = "UR-Heart Sanctuary"

    @model_validator(mode="after")
    def validate_production_invariants(self) -> "Settings":
        if self.ENVIRONMENT not in ("development", "test"):
            if self.DATABASE_URL.lower().startswith("sqlite"):
                raise ValueError("Persistent PostgreSQL database URL is required outside development and test.")
            if self.SECRET_KEY == "ur-heart-sanctuary-local-secret-key-32b" or len(self.SECRET_KEY) < 32:
                raise ValueError("A secure, non-default SECRET_KEY with at least 32 characters is required in staging and production.")
        return self

settings = Settings()
