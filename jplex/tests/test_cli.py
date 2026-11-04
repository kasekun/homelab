from __future__ import annotations

import click
from click.testing import CliRunner

from jplex import cli
from jplex.catalog import content_uri
from jplex.models import CatalogItem
from jplex.plex_api import PlexAPIError


def item(rating_key: int, kind: str) -> CatalogItem:
    return CatalogItem(
        rating_key=rating_key,
        type=kind,  # type: ignore[arg-type]
        title="Title",
        year=None,
        library=None,
        uri=content_uri("machine", kind, rating_key),
    )


def test_omitted_mode_resumes_movies_and_shows_but_restarts_playlists() -> None:
    assert cli.effective_mode(item(1, "movie"), None) == "resume"
    assert cli.effective_mode(item(2, "show"), None) == "resume"
    assert cli.effective_mode(item(3, "playlist"), None) == "restart"
    assert cli.effective_mode(item(1, "movie"), "shuffle") == "shuffle"


def test_mode_aliases_are_mutually_exclusive() -> None:
    assert cli.requested_mode(None, from_start=True, shuffle=False) == "restart"
    assert cli.requested_mode(None, from_start=False, shuffle=True) == "shuffle"

    try:
        cli.requested_mode("resume", from_start=True, shuffle=False)
    except click.ClickException as error:
        assert "mutually exclusive" in str(error)
    else:
        raise AssertionError("expected mutually exclusive mode error")


def test_cache_refresh_reports_plex_errors_as_cli_errors(monkeypatch) -> None:
    def fail_refresh(*args, **kwargs):
        raise PlexAPIError("plex is down")

    monkeypatch.setattr(cli, "refresh_catalog", fail_refresh)

    result = CliRunner().invoke(cli.main, ["cache", "refresh"])

    assert result.exit_code == 1
    assert "Error: plex is down" in result.output
    assert result.exception is not None
    assert not isinstance(result.exception, PlexAPIError)
