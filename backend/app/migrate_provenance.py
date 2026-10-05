"""Explicit, idempotent SQLite development migration; never infers provenance."""

from sqlalchemy import inspect

from app.database import engine


def migrate(target_engine=engine):
    if target_engine.dialect.name != "sqlite":
        raise RuntimeError("This development migration supports SQLite only.")
    inspector = inspect(target_engine)
    if "orders" not in inspector.get_table_names():
        return
    if "provenance" in {column["name"] for column in inspector.get_columns("orders")}:
        return
    with target_engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE orders ADD COLUMN provenance VARCHAR(20) NOT NULL "
            "DEFAULT 'unknown' CHECK (provenance IN "
            "('demo', 'square_import', 'manual', 'unknown'))"
        )


if __name__ == "__main__":
    migrate()
    print("Order provenance migration complete; existing rows remain unknown.")
