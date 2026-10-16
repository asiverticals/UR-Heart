from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Deployment Environment
    APP_NAME: str = "UR-Heart Core Engine"
    PROJECT_NAME: str = "UR-Heart Sanctuary"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    PORT: int = 10000
    TESTING: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database Persistence & Supabase Pooler (Port 6543)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urheart"
    SUPABASE_PGBOUNCER_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_STORAGE_BUCKET: str = "ur-heart-media"
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # Authentication & JWT Tokens
    JWT_SECRET_KEY: str = "ur-heart-sanctuary-local-secret-key-32b"
    SECRET_KEY: str = "ur-heart-sanctuary-local-secret-key-32b"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    WS_TICKET_EXPIRE_SECONDS: int = 60
    WS_BASE_URL: str = "wss://urheart.app/ws/chat"
    CONTACT_BRIDGE_SECRET_KEY: Optional[str] = None
    TRUSTED_PROXIES: str = "127.0.0.1,::1"
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
    RAZORPAY_MERCHANT_NAME: str = "UR-Heart Sanctuary"
    RAZORPAY_THEME_COLOR: str = "#2E6F5E"
    STRIPE_WEBHOOK_SECRET: str = ""
    REVENUECAT_WEBHOOK_SECRET: str = ""
    CASHFREE_CLIENT_ID: str = ""
    CASHFREE_SECRET_KEY: str = ""

    # 5-Network Ad SSV Waterfall Credentials
    ADMOB_VERIFIER_KEYS_URL: str = "https://www.gstatic.com/admob/reward/verifier-keys.json"
    META_APP_SECRET: str = ""
    META_AUDIENCE_SSV_SECRET: str = ""
    UNITY_ADS_SECRET: str = ""
    UNITY_ADS_SSV_SECRET: str = ""
    LIFTOFF_API_SECRET: str = ""
    LIFTOFF_SSV_SECRET: str = ""
    CHARTBOOST_APP_SECRET: str = ""
    CHARTBOOST_SSV_SECRET: str = ""

    # Cloudflare R2 Media Storage (Optional Secondary Adapter)
    CLOUDFLARE_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "ur-heart-media"
    R2_PUBLIC_DOMAIN: str = "https://media.urheart.app"

    # Google Auth, Firebase Admin & Storage
    GOOGLE_SERVER_CLIENT_ID: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_STORAGE_BUCKET: str = "ur-heart-44b46.firebasestorage.app"
    FIREBASE_CREDENTIALS_PATH: str = "backend/serviceAccountKey.json"
    FIREBASE_SERVICE_ACCOUNT_B64: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = "{}"
    FIREBASE_WEB_API_KEY: str = ""

    # AI Reasoning Cluster & Voice Engines
    GROQ_API_KEY: str = ""
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_VOICE_API_KEY: str = ""
    GROQ_WHISPER_URL: str = "https://api.groq.com/openai/v1/audio/transcriptions"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    GEMINI_API_KEY: str = ""
    GEMINI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/models"

    # Transactional Email Waterfall
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "UR-Heart Sanctuary <verify@urheart.app>"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "UR-Heart Sanctuary <verify@urheart.app>"
    BREVO_API_KEY: str = ""
    BREVO_SMTP_HOST: str = "smtp-relay.brevo.com"
    BREVO_SMTP_PORT: int = 587
    BREVO_SMTP_USER: str = ""
    BREVO_SMTP_PASSWORD: str = ""
    TESTMAIL_API_KEY: str = ""
    TESTMAIL_NAMESPACE: str = ""

    # Superuser & Sentinel Gate
    SUPERADMIN_EMAIL: str = ""
    ADMIN_SUPERUSER_EMAIL: str = ""
    SUPERADMIN_SECRET_KEY: str = ""

    # Sentry Error Monitoring
    SENTRY_DSN: str = ""

    @model_validator(mode="after")
    def validate_production_invariants(self) -> "Settings":
        if self.APP_NAME and not self.PROJECT_NAME:
            self.PROJECT_NAME = self.APP_NAME
        elif self.PROJECT_NAME and not self.APP_NAME:
            self.APP_NAME = self.PROJECT_NAME

        if self.SUPABASE_PGBOUNCER_URL and (
            not self.DATABASE_URL or self.DATABASE_URL == "postgresql+asyncpg://postgres:postgres@localhost:5432/urheart"
        ):
            self.DATABASE_URL = self.SUPABASE_PGBOUNCER_URL

        # Ad SSV alias harmonization
        if not self.META_APP_SECRET and self.META_AUDIENCE_SSV_SECRET:
            self.META_APP_SECRET = self.META_AUDIENCE_SSV_SECRET
        if not self.UNITY_ADS_SECRET and self.UNITY_ADS_SSV_SECRET:
            self.UNITY_ADS_SECRET = self.UNITY_ADS_SSV_SECRET
        if not self.CHARTBOOST_APP_SECRET and self.CHARTBOOST_SSV_SECRET:
            self.CHARTBOOST_APP_SECRET = self.CHARTBOOST_SSV_SECRET
        if not self.LIFTOFF_API_SECRET and self.LIFTOFF_SSV_SECRET:
            self.LIFTOFF_API_SECRET = self.LIFTOFF_SSV_SECRET

        # Superadmin alias harmonization
        if not self.ADMIN_SUPERUSER_EMAIL and self.SUPERADMIN_EMAIL:
            self.ADMIN_SUPERUSER_EMAIL = self.SUPERADMIN_EMAIL
        elif not self.SUPERADMIN_EMAIL and self.ADMIN_SUPERUSER_EMAIL:
            self.SUPERADMIN_EMAIL = self.ADMIN_SUPERUSER_EMAIL

        # Secret key fallback
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
        if (
            not settings.JWT_SECRET_KEY
            or len(settings.JWT_SECRET_KEY) < 32
            or settings.JWT_SECRET_KEY == "ur-heart-sanctuary-local-secret-key-32b"
            or settings.JWT_SECRET_KEY.startswith("replace_with_")
            or settings.JWT_SECRET_KEY.startswith("placeholder_")
        ):
            raise RuntimeError("Fatal: JWT_SECRET_KEY must be at least 32 characters and a real cryptographic secret in production.")
        if settings.DATABASE_URL.lower().startswith("sqlite"):
            raise RuntimeError("Fatal: Persistent PostgreSQL database required in production.")
        if not settings.SUPABASE_URL:
            raise RuntimeError("Fatal: SUPABASE_URL is required in production.")
        if not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("Fatal: SUPABASE_SERVICE_ROLE_KEY is required in production.")
        if not settings.SUPERADMIN_SECRET_KEY or settings.SUPERADMIN_SECRET_KEY.startswith("placeholder_"):
            raise RuntimeError("Fatal: SUPERADMIN_SECRET_KEY is required and must not be a placeholder in production.")
        if not settings.CONTACT_BRIDGE_SECRET_KEY:
            raise RuntimeError("Fatal: CONTACT_BRIDGE_SECRET_KEY is required in production.")
