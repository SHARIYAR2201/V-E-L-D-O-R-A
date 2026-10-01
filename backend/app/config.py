from pathlib import Path
from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{ROOT / 'veldora.db'}"
    redis_url: str | None = None
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    google_client_id: str | None = None
    cors_origins: str = "http://localhost:3000"
    data_dir: str = str(ROOT.parent / "data")
    artifacts_dir: str = str(ROOT / "artifacts")
    admin_emails: str = ""  # comma separated; these accounts get the admin role on register

    model_config = {"env_file": ".env", "env_prefix": "VELDORA_"}


settings = Settings()
