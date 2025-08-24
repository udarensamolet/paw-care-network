from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)  # ensure instance exists
DB_FILE = INSTANCE_DIR / "app.db"


def _get_database_uri() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    return f"sqlite:///{DB_FILE.as_posix()}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB uploads
