from __future__ import annotations

from pathlib import Path

from jplex.config import load_settings


def test_settings_load_env_file_and_normalize_adb_device(
    tmp_path: Path, monkeypatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "JPLEX_PLEX_URL=http://plex.local:32400/\n"
        "JPLEX_PLEX_TOKEN=super-secret\n"
        "JPLEX_ADB_DEVICE=192.168.1.126\n"
        "JPLEX_LAUNCH_TIMEOUT_SECONDS=5.5\n"
        "JPLEX_ROUTE_SETTLE_MS=2500\n"
    )
    monkeypatch.delenv("JPLEX_PLEX_URL", raising=False)
    monkeypatch.delenv("JPLEX_PLEX_TOKEN", raising=False)
    monkeypatch.delenv("JPLEX_ADB_DEVICE", raising=False)
    monkeypatch.delenv("JPLEX_LAUNCH_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("JPLEX_ROUTE_SETTLE_MS", raising=False)

    settings = load_settings(env_file=env_file)

    assert settings.plex_url == "http://plex.local:32400"
    assert settings.plex_token is not None
    assert settings.plex_token.get_secret_value() == "super-secret"
    assert str(settings.plex_token) == "**********"
    assert settings.adb_device == "192.168.1.126:5555"
    assert settings.launch_timeout_seconds == 5.5
    assert settings.route_settle_ms == 2500


def test_cli_overrides_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "JPLEX_PLEX_URL=http://from-env:32400\nJPLEX_LAUNCH_TIMEOUT_SECONDS=8\n"
    )

    settings = load_settings(
        env_file=env_file,
        plex_url="http://from-cli:32400",
        launch_timeout_seconds=12,
    )

    assert settings.plex_url == "http://from-cli:32400"
    assert settings.launch_timeout_seconds == 12


def test_launch_timeout_defaults_to_12(monkeypatch) -> None:
    monkeypatch.delenv("JPLEX_LAUNCH_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("JPLEX_ROUTE_SETTLE_MS", raising=False)

    settings = load_settings(env_file=Path("/dev/null"))

    assert settings.launch_timeout_seconds == 12
    assert settings.route_settle_ms == 900
