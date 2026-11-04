from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .models import CatalogItem
from .plex_api import PlexClient, PlexMedia


BASE_URI = "server://{machine}/com.plexapp.plugins.library"


@dataclass(frozen=True)
class Catalog:
    machine_id: str
    metadata: dict[str, Any]
    items: list[CatalogItem]


def content_uri(machine_id: str, item_type: str, rating_key: int) -> str:
    base = BASE_URI.format(machine=machine_id)
    if item_type == "playlist":
        return f"{base}/playlists/{rating_key}"
    return f"{base}/library/metadata/{rating_key}"


def item_from_media(
    machine_id: str, media: PlexMedia, item_type: str | None = None
) -> CatalogItem:
    kind = item_type or media.type
    return CatalogItem(
        rating_key=media.rating_key,
        type=kind,  # type: ignore[arg-type]
        title=media.title,
        year=media.year,
        library=media.library,
        key=media.key,
        edition=media.edition,
        uri=content_uri(machine_id, kind, media.rating_key),
    )


def refresh_catalog(client: PlexClient, cache_path: Path) -> Catalog:
    machine_id = client.machine_id()
    items: list[CatalogItem] = []
    counts: dict[str, int] = {}

    for section_key, library in client.sections():
        for media in client.section_items(section_key, library):
            if media.type not in {"movie", "show"}:
                continue
            item = item_from_media(machine_id, media)
            items.append(item)
            counts[item.type] = counts.get(item.type, 0) + 1

    for playlist in client.playlists():
        item = item_from_media(machine_id, playlist, "playlist")
        items.append(item)
        counts["playlist"] = counts.get("playlist", 0) + 1

    metadata = {
        "machineId": machine_id,
        "generatedAt": datetime.now(UTC).isoformat(),
        "plexUrl": client.base_url,
        "counts": counts,
    }
    catalog = Catalog(machine_id=machine_id, metadata=metadata, items=items)
    write_catalog(cache_path, catalog)
    return catalog


def load_catalog(cache_path: Path) -> Catalog:
    data = json.loads(cache_path.read_text())
    return Catalog(
        machine_id=data["metadata"]["machineId"],
        metadata=data["metadata"],
        items=[CatalogItem.from_json(item) for item in data["items"]],
    )


def write_catalog(cache_path: Path, catalog: Catalog) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            {
                "metadata": catalog.metadata,
                "items": [item.to_json() for item in catalog.items],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=cache_path.parent,
            prefix=f".{cache_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(data)
        temp_path.replace(cache_path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
