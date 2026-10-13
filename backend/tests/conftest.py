import uuid
from datetime import date, datetime, timezone
from typing import AsyncGenerator, Callable
import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.app.models.domain import Base, User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # Enable SQLite foreign key constraint enforcement
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session_factory() as session:
        yield session

@pytest.fixture
def make_user() -> Callable[..., User]:
    def _make_user(**kwargs) -> User:
        user_id = kwargs.get("id", uuid.uuid4())
        unique_suffix = str(uuid.uuid4())[:8]
        defaults = {
            "id": user_id,
            "auth_id": kwargs.get("auth_id", uuid.uuid4()),
            "email": kwargs.get("email", f"seeker_{unique_suffix}@urheart.app"),
            "full_name": "Radha Raman",
            "dob": date(2000, 1, 1),
            "gender": "Woman",
            "interested_in": "Men",
            "contact_bridge_type": "whatsapp",
            "contact_bridge_encrypted": "enc_whatsapp_token_abc123",
            "location_name": "Saket, Ayodhya",
            "bio": "Walking the path of sincere kinship.",
            "profession": "Devotee & Architect",
            "education": "Gurukul Vishwavidyalaya",
            "referral_code": f"REF_{unique_suffix}",
            "photos": ["https://media.urheart.app/users/radha/primary.jpg"],
            "role": "user",
        }
        defaults.update(kwargs)
        return User(**defaults)
    return _make_user
