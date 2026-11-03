from __future__ import annotations

from click.testing import CliRunner

from jplex import cli
from jplex.plex_api import PlexAPIError


def test_cache_refresh_reports_plex_errors_as_cli_errors(monkeypatch) -> None:
    def fail_refresh(*args, **kwargs):
        raise PlexAPIError("plex is down")

    monkeypatch.setattr(cli, "refresh_catalog", fail_refresh)

    result = CliRunner().invoke(cli.main, ["cache", "refresh"])

    assert result.exit_code == 1
    assert "Error: plex is down" in result.output
    assert result.exception is not None
    assert not isinstance(result.exception, PlexAPIError)
