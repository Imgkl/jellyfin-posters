from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jellyfin_url: str = "http://localhost:8096"
    jellyfin_username: str = ""
    jellyfin_password: str = ""
    db_path: str = "/data/progress.db"
    host: str = "0.0.0.0"
    port: int = 8000

    @field_validator("jellyfin_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
