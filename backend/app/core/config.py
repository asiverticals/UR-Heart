from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Deployment Environment
    ENVIRONMENT: str = "development"
    PORT: int = 10000
    TESTING: bool = False
    PROJECT_NAME: str = "UR-Heart Sanctuary"

    # Database Persistence
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urheart"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Authentication & JWT Tokens
    JWT_SECRET_KEY: str = "ur-heart-sanctuary-local-secret-key-32b"
    SECRET_KEY: str = "ur-heart-sanctuary-local-secret-key-32b"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    WS_TICKET_EXPIRE_SECONDS: int = 60

    # Scale Condition Feature Gates (Condition C1 & C2)
    BLIND_DATE_MIN_ACTIVE_USERS: int = 1000000
    ENABLE_BLIND_DATE_OVERRIDE: bool = False
    ENABLE_GLOBAL_USD_BILLING: bool = False
    PASSPORT_MIN_ACTIVE_USERS: int = 1000000
    ENABLE_PASSPORT_OVERRIDE: bool = False

    # Monetization & Payment Gateways
    PAYMENT_GATEWAY: str = "razorpay"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    CASHFREE_CLIENT_ID: str = ""
    CASHFREE_SECRET_KEY: str = ""

    # Cloudflare R2 Media Storage
    CLOUDFLARE_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "ur-heart-media"
    R2_PUBLIC_DOMAIN: str = "https://media.urheart.app"

    # Google Auth & Firebase Cloud Messaging
    GOOGLE_SERVER_CLIENT_ID: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = "{}"

    # AI Reasoning Cluster
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Superuser Governance
    ADMIN_SUPERUSER_EMAIL: str = "asiverticals@gmail.com"

    @model_validator(mode="after")
    def validate_production_invariants(self) -> "Settings":
        if self.SECRET_KEY != self.JWT_SECRET_KEY and self.JWT_SECRET_KEY != "ur-heart-sanctuary-local-secret-key-32b":
            self.SECRET_KEY = self.JWT_SECRET_KEY
        if self.ENVIRONMENT not in ("development", "test"):
            if self.DATABASE_URL.lower().startswith("sqlite"):
                raise ValueError("Persistent PostgreSQL database URL is required outside development and test.")
            if self.JWT_SECRET_KEY == "ur-heart-sanctuary-local-secret-key-32b" or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("A secure, non-default JWT_SECRET_KEY with at least 32 characters is required in staging and production.")
        return self

settings = Settings()

def validate_production_secrets() -> None:
    """Boot-time validation for production environments; aborts immediately on weak or missing secrets."""
    if settings.ENVIRONMENT == "production":
        if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32 or settings.JWT_SECRET_KEY == "ur-heart-sanctuary-local-secret-key-32b":
            raise RuntimeError("Fatal: JWT_SECRET_KEY must be at least 32 characters in production.")
        if settings.DATABASE_URL.lower().startswith("sqlite"):
            raise RuntimeError("Fatal: Persistent PostgreSQL database required in production.")
        if not settings.SUPABASE_URL:
            raise RuntimeError("Fatal: SUPABASE_URL is required in production.")
        if not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("Fatal: SUPABASE_SERVICE_ROLE_KEY is required in production.")
