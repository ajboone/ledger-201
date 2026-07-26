from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = "sqlite:///./ledger201.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


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