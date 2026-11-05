from __future__ import annotations

import os
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_cache_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "jplex" / "catalog.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        cli_parse_args=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    plex_url: str = Field(
        default="http://127.0.0.1:32400",
        validation_alias=AliasChoices("plex_url", "JPLEX__PLEX_URL"),
    )
    plex_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("plex_token", "JPLEX__PLEX_TOKEN"),
    )
    adb_bin: str = Field(
        default="adb",
        validation_alias=AliasChoices("adb_bin", "JPLEX__ADB_BIN"),
    )
    adb_device: str | None = Field(
        default=None,
        validation_alias=AliasChoices("adb_device", "JPLEX__ADB_DEVICE_ADDRESS"),
    )
    shield_package: str = Field(
        default="com.plexapp.android",
        validation_alias=AliasChoices("shield_package", "JPLEX__SHIELD_PACKAGE"),
    )
    shield_activity: str = Field(
        default="com.plexapp.android/tv.plex.app.MainActivity",
        validation_alias=AliasChoices("shield_activity", "JPLEX__SHIELD_ACTIVITY"),
    )
    launch_timeout_seconds: float = Field(
        default=12,
        gt=0,
        validation_alias=AliasChoices(
            "launch_timeout_seconds",
            "JPLEX__LAUNCH_TIMEOUT_SECONDS",
        ),
    )
    route_settle_ms: int = Field(
        default=900,
        ge=0,
        validation_alias=AliasChoices("route_settle_ms", "JPLEX__ROUTE_SETTLE_MS"),
    )
    show_audio_preview_grace_ms: int = Field(
        default=1800,
        ge=0,
        validation_alias=AliasChoices(
            "show_audio_preview_grace_ms",
            "JPLEX__SHOW__AUDIO_PREVIEW_GRACE_MS",
        ),
    )
    cache_path: Path = Field(
        default_factory=default_cache_path,
        validation_alias=AliasChoices("cache_path", "JPLEX__CACHE_PATH"),
    )

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
