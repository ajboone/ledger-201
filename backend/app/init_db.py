"""Create missing tables only: python -m app.init_db. Never seeds or resets data."""

from app import models  # noqa: F401 -- register all mapped tables
from app.database import Base, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Missing database tables created; existing records preserved. No data seeded.")


if __name__ == "__main__":
    main()
