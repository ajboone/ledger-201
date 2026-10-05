import os
from pathlib import Path

import pytest

from app import config


def test_environment_loader_reads_dotenv_when_process_value_is_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=test-only-placeholder\nOPENAI_MODEL=test-model-placeholder\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    config.load_environment(env_file)

    assert os.environ["OPENAI_API_KEY"] == "test-only-placeholder"
    assert os.environ["OPENAI_MODEL"] == "test-model-placeholder"


def test_process_environment_values_take_precedence_over_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=dotenv-placeholder\nOPENAI_MODEL=dotenv-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "process-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "process-model")

    config.load_environment(env_file)

    assert os.environ["OPENAI_API_KEY"] == "process-placeholder"
    assert os.environ["OPENAI_MODEL"] == "process-model"


def test_backend_env_path_is_resolved_from_config_file_not_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_env_file = config.BACKEND_ENV_FILE
    assert backend_env_file == Path(__file__).resolve().parents[1] / ".env"

    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_MODEL=path-independent-test-model\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(config, "BACKEND_ENV_FILE", env_file)
    monkeypatch.chdir(tmp_path)
    config.load_environment()

    assert os.environ["OPENAI_MODEL"] == "path-independent-test-model"
