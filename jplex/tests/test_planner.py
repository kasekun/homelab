from __future__ import annotations

from jplex.catalog import content_uri, item_from_media
from jplex.models import CatalogItem
from jplex.planner import plan_playback, watch_url
from jplex.plex_api import PlexMedia


class FakePlex:
    def __init__(self) -> None:
        self.movie_key = 1
        self.show_key = 10
        self.movie = PlexMedia(1, "Movie", "movie", view_offset_ms=125000)
        self.on_deck_episode = PlexMedia(
            21, "Episode Two", "episode", view_offset_ms=92000
        )

    def metadata(self, rating_key: int) -> PlexMedia:
        assert rating_key == self.movie_key
        return self.movie

    def on_deck(self, show_rating_key: int) -> PlexMedia:
        assert show_rating_key == self.show_key
        return self.on_deck_episode


def item(rating_key: int, kind: str, title: str = "Title") -> CatalogItem:
    return CatalogItem(
        rating_key=rating_key,
        type=kind,  # type: ignore[arg-type]
        title=title,
        year=None,
        library=None,
        uri=content_uri("machine", kind, rating_key),
    )


def test_watch_url_encodes_playlist_key_offset_and_shuffle() -> None:
    url = watch_url(
        "server://machine/com.plexapp.plugins.library/playlists/49444",
        offset=12,
        key="/library/metadata/22",
        shuffle=True,
    )

    assert (
        "server%3A%2F%2Fmachine%2Fcom.plexapp.plugins.library%2Fplaylists%2F49444"
        in url
    )
    assert "key=%2Flibrary%2Fmetadata%2F22" in url
    assert "offset=12" in url
    assert "shuffle=1" in url


def test_movie_resume_uses_view_offset_seconds() -> None:
    plan = plan_playback(item(1, "movie", "Movie"), "resume", FakePlex(), "machine")

    assert plan.offset == 125
    assert plan.uri.endswith("/library/metadata/1")


def test_show_resume_uses_on_deck_episode_uri_not_show_key() -> None:
    plan = plan_playback(item(10, "show", "Show"), "resume", FakePlex(), "machine")

    assert plan.uri.endswith("/library/metadata/21")
    assert plan.key is None
    assert plan.offset == 92
    assert plan.target_rating_key == 21


def test_playlist_uri_comes_from_rating_key_not_api_key() -> None:
    playlist = item_from_media(
        "machine",
        PlexMedia(49444, "Futurama", "playlist", key="/playlists/49444/items"),
        "playlist",
    )

    assert (
        playlist.uri == "server://machine/com.plexapp.plugins.library/playlists/49444"
    )
    assert plan_playback(playlist, "shuffle", None, "machine").shuffle is True
