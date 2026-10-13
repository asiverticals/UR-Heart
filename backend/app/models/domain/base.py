from datetime import datetime
from sqlalchemy import MetaData, DateTime, BigInteger, Integer, Uuid
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Reusable timezone-aware timestamp type with SQLite compatibility
TIMESTAMPTZ = TIMESTAMP(timezone=True).with_variant(DateTime(timezone=True), "sqlite")

# Reusable 64-bit integer primary key with SQLite autoincrement compatibility
BigIntPK = BigInteger().with_variant(Integer, "sqlite")

# Reusable dialect-agnostic UUID type (native UUID in PostgreSQL, CHAR(32) in SQLite)
UniversalUUID = Uuid(as_uuid=True)

# PostgreSQL constraint naming conventions
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "chk_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
