import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import inspect

from app import config, database


def test_database_url_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////var/lib/ledger201/ledger201.db")
    assert config.get_database_url() == "sqlite:////var/lib/ledger201/ledger201.db"


def test_database_url_local_fallback(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert config.get_database_url() == "sqlite:///./ledger201.db"


def test_sqlite_engine_allows_cross_thread_access(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    engine = database.create_database_engine(f"sqlite:///{tmp_path / 'thread.db'}")
    try:
        with engine.connect() as connection:
            with ThreadPoolExecutor(max_workers=1) as executor:
                assert executor.submit(lambda: connection.exec_driver_sql("SELECT 1").scalar()).result() == 1
    finally:
        engine.dispose()


def test_postgresql_engine_receives_no_sqlite_arguments():
    # No PostgreSQL driver/server needed to verify driver-specific configuration.
    with patch.object(database, "create_engine") as create:
        database.create_database_engine("postgresql+psycopg://localhost/ledger")
    create.assert_called_once_with("postgresql+psycopg://localhost/ledger")


def test_health_is_lightweight_and_non_sensitive(client):
    with patch.object(database.engine, "connect", side_effect=AssertionError("No DB call")):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fresh_startup_and_explicit_init_preserve_data_without_demo_seed(tmp_path):
    target = tmp_path / "production.db"
    environment = {**os.environ, "DATABASE_URL": f"sqlite:///{target}"}
    backend = Path(__file__).resolve().parents[1]
    startup = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "with TestClient(app) as client:\n"
        "    assert client.get('/health').json() == {'status': 'ok'}\n"
    )
    subprocess.run([sys.executable, "-c", startup], cwd=backend, env=environment, check=True, capture_output=True)
    engine = database.create_database_engine(environment["DATABASE_URL"])
    try:
        tables = inspect(engine).get_table_names()
        assert {"orders", "locations", "square_sales_reports"} <= set(tables)
        with engine.begin() as connection:
            for table in tables:
                assert connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table}"').scalar() == 0
            connection.exec_driver_sql("INSERT INTO vendors (name) VALUES ('Existing real vendor')")
        subprocess.run([sys.executable, "-m", "app.init_db"], cwd=backend, env=environment, check=True, capture_output=True)
        subprocess.run([sys.executable, "-c", startup], cwd=backend, env=environment, check=True, capture_output=True)
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT name FROM vendors").scalar() == "Existing real vendor"
            for table in tables:
                assert connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table}"').scalar() == (1 if table == "vendors" else 0)
    finally:
        engine.dispose()
