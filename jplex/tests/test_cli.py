from __future__ import annotations

import click
from click.testing import CliRunner

from jplex import cli
from jplex.catalog import content_uri
from jplex.models import CatalogItem, PlaybackPlan
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


def test_play_prepares_before_planning_resume(monkeypatch) -> None:
    events: list[str] = []
    target = item(10, "show")
    plan = PlaybackPlan(
        item=target,
        mode="resume",
        uri=target.uri,
        url="https://watch.plex.tv/watch/video?uri=x&offset=1",
        details_url="https://watch.plex.tv/libraries/m/show/item/10",
        offset=1,
    )

    class FakeLauncher:
        def __init__(self, settings) -> None:
            pass

        def prepare(self) -> None:
            events.append("prepare")

        def start(
            self,
            url: str,
            details_url: str | None = None,
            *,
            release_details_preview: bool = False,
        ) -> None:
            events.append(f"start:{release_details_preview}")

    def build_plan(*args, **kwargs):
        events.append("plan")
        return plan

    monkeypatch.setattr(cli, "get_catalog", lambda ctx: object())
    monkeypatch.setattr(cli, "resolve_or_exit", lambda *args: target)
    monkeypatch.setattr(cli, "build_plan_or_exit", build_plan)
    monkeypatch.setattr(cli, "ADBLauncher", FakeLauncher)

    result = CliRunner().invoke(cli.main, ["play", "show"])

    assert result.exit_code == 0
    assert events == ["prepare", "plan", "start:True"]
