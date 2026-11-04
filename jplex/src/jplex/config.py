from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_cache_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "jplex" / "catalog.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JPLEX_",
        cli_parse_args=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    plex_url: str = "http://127.0.0.1:32400"
    plex_token: SecretStr | None = None
    adb_bin: str = "adb"
    adb_device: str | None = None
    shield_package: str = "com.plexapp.android"
    shield_activity: str = "com.plexapp.android/tv.plex.app.MainActivity"
    launch_timeout_seconds: float = Field(default=12, gt=0)
    cache_path: Path = Field(default_factory=default_cache_path)

    @field_validator("plex_url")
    @classmethod
    def strip_plex_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("adb_device")
    @classmethod
    def normalize_adb_device(cls, value: str | None) -> str | None:
        if not value:
            return value
        value = value.strip()
        if ":" not in value:
            return f"{value}:5555"
        return value


def load_settings(env_file: Path | None = None, **overrides: object) -> Settings:
    cleaned = {key: value for key, value in overrides.items() if value is not None}
    return Settings(_env_file=env_file or PROJECT_ROOT / ".env", **cleaned)
