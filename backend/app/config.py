from pathlib import Path

from dotenv import load_dotenv


BACKEND_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_environment(env_file: Path | None = None) -> None:
    """Load backend environment settings without overriding process values."""

    load_dotenv(
        dotenv_path=BACKEND_ENV_FILE if env_file is None else env_file,
        override=False,
    )


load_environment()
