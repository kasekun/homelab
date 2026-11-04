from __future__ import annotations

from urllib.parse import urlencode

from .catalog import content_uri
from .models import CatalogItem, PlayMode, PlaybackPlan
from .plex_api import PlexClient, PlexMedia


class PlanningError(RuntimeError):
    pass


def details_url(machine_id: str, item: CatalogItem) -> str | None:
    if item.type == "show":
        # Show details can start preview playback, causing the watch link to ignore offset.
        return None
    if item.type == "playlist":
        path = f"playlist/{item.rating_key}"
    else:
        path = f"{item.type}/item/{item.rating_key}"
    return f"https://watch.plex.tv/libraries/{machine_id}/{path}"


def watch_url(
    uri: str, offset: int = 0, key: str | None = None, shuffle: bool = False
) -> str:
    params: dict[str, str] = {"uri": uri, "offset": str(offset)}
    if key:
        params["key"] = key
    if shuffle:
        params["shuffle"] = "1"
    return "https://watch.plex.tv/watch/video?" + urlencode(params)


def plan_playback(
    item: CatalogItem, mode: PlayMode, client: PlexClient | None, machine_id: str
) -> PlaybackPlan:
    if item.type == "movie":
        return _movie_plan(item, mode, client, machine_id)
    if item.type == "show":
        return _show_plan(item, mode, client, machine_id)
    if item.type == "playlist":
        return _playlist_plan(item, mode, machine_id)
    raise PlanningError(f"Unsupported item type: {item.type}")


def _movie_plan(
    item: CatalogItem, mode: PlayMode, client: PlexClient | None, machine_id: str
) -> PlaybackPlan:
    if mode not in {"restart", "resume"}:
        raise PlanningError(f"A movie has no {mode} mode.")
    offset = 0
    if mode == "resume":
        if client is None:
            raise PlanningError("Movie resume requires Plex API access.")
        media = client.metadata(item.rating_key)
        offset = (media.view_offset_ms if media else 0) // 1000
    return _plan(item, mode, item.uri, machine_id, offset=offset)


def _show_plan(
    item: CatalogItem, mode: PlayMode, client: PlexClient | None, machine_id: str
) -> PlaybackPlan:
    if mode == "restart":
        return _plan(item, mode, item.uri, machine_id)
    if mode == "shuffle":
        return _plan(item, mode, item.uri, machine_id, shuffle=True)
    if mode == "resume":
        if client is None:
            raise PlanningError("Show resume requires Plex API access.")
        episode = client.on_deck(item.rating_key)
        if episode is None:
            return _plan(item, mode, item.uri, machine_id)
        return _episode_plan(
            item, mode, episode, machine_id, episode.view_offset_ms // 1000
        )
    raise PlanningError(f"A show has no {mode} mode.")


def _playlist_plan(item: CatalogItem, mode: PlayMode, machine_id: str) -> PlaybackPlan:
    if mode not in {"restart", "shuffle"}:
        raise PlanningError(f"A playlist has no {mode} mode.")
    return _plan(item, mode, item.uri, machine_id, shuffle=mode == "shuffle")


def _episode_plan(
    item: CatalogItem,
    mode: PlayMode,
    episode: PlexMedia,
    machine_id: str,
    offset: int,
) -> PlaybackPlan:
    uri = content_uri(machine_id, "movie", episode.rating_key)
    return _plan(
        item,
        mode,
        uri,
        machine_id,
        offset=offset,
        target_rating_key=episode.rating_key,
        target_title=episode.title,
    )


def _plan(
    item: CatalogItem,
    mode: PlayMode,
    uri: str,
    machine_id: str,
    offset: int = 0,
    key: str | None = None,
    shuffle: bool = False,
    target_rating_key: int | None = None,
    target_title: str | None = None,
) -> PlaybackPlan:
    return PlaybackPlan(
        item=item,
        mode=mode,
        uri=uri,
        key=key,
        offset=offset,
        shuffle=shuffle,
        target_rating_key=target_rating_key,
        target_title=target_title,
        url=watch_url(uri, offset, key, shuffle),
        details_url=details_url(machine_id, item),
    )
