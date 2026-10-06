from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_database_url


DATABASE_URL = get_database_url()


def create_database_engine(database_url: str) -> Engine:
    """Keep driver-specific options isolated for future database backends."""
    if make_url(database_url).get_backend_name() == "sqlite":
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


engine = create_database_engine(DATABASE_URL)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class inherited by all database models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Provide a database session and close it after the request."""

    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()
