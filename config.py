from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)  
DB_FILE = INSTANCE_DIR / "app.db"

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_FILE.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
