# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (or current working directory)
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # fallback to any .env in cwd
    load_dotenv()

def get_env(key: str, default=None):
    val = os.environ.get(key, default)
    if val is None:
        return default
    return val

class Settings:
    MYSQL_USER: str = get_env("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = get_env("MYSQL_PASSWORD", "")
    MYSQL_HOST: str = get_env("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: int = int(get_env("MYSQL_PORT", 3306))
    MYSQL_DB: str = get_env("MYSQL_DB", "quantdb")

    REDIS_HOST: str = get_env("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: int = int(get_env("REDIS_PORT", 6379))
    REDIS_DB: int = int(get_env("REDIS_DB", 0))

    API_TITLE: str = get_env("API_TITLE", "Quant Analytics API")
    API_VERSION: str = get_env("API_VERSION", "1.0.0")

def get_settings() -> Settings:
    return Settings()
