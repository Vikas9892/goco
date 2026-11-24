import os
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auction.db")

engine = create_engine(
    DATABASE_URL,
    # FastAPI runs sync endpoints in a threadpool; SQLite connections must be shareable across threads.
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    """Stores UTC and always returns timezone-aware UTC (SQLite would otherwise drop tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        return value.astimezone(UTC) if value else value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
