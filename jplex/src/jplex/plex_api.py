from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable

import httpx
from pydantic import SecretStr


class PlexAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlexMedia:
    rating_key: int
    title: str
    type: str
    key: str | None = None
    year: int | None = None
    library: str | None = None
    view_offset_ms: int = 0
    edition: str | None = None


def _int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _media_from_element(element: ET.Element, library: str | None = None) -> PlexMedia:
    return PlexMedia(
        rating_key=int(element.attrib["ratingKey"]),
        title=element.attrib.get("title", ""),
        type=element.attrib.get("type", ""),
        key=element.attrib.get("key"),
        year=_int(element.attrib.get("year")),
        library=library,
        view_offset_ms=int(element.attrib.get("viewOffset") or 0),
        edition=element.attrib.get("editionTitle"),
    )


class PlexClient:
    def __init__(
        self,
        base_url: str,
        token: SecretStr | str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = (
            token.get_secret_value() if isinstance(token, SecretStr) else token
        )
        self._client = client or httpx.Client(timeout=10)

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Accept": "application/xml"}
        if self._token:
            headers["X-Plex-Token"] = self._token
        return headers

    def get_xml(self, path: str, **params: object) -> ET.Element:
        try:
            response = self._client.get(
                f"{self.base_url}{path}",
                params={
                    key: value for key, value in params.items() if value is not None
                },
                headers=self.headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise PlexAPIError(self._redact(str(error))) from error
        return ET.fromstring(response.content)

    def machine_id(self) -> str:
        root = self.get_xml("/")
        value = root.attrib.get("machineIdentifier")
        if not value:
            raise PlexAPIError("Plex root response did not include machineIdentifier")
        return value

    def sections(self) -> list[tuple[str, str]]:
        root = self.get_xml("/library/sections")
        return [
            (node.attrib["key"], node.attrib.get("title", ""))
            for node in root.findall("Directory")
            if node.attrib.get("type") in {"movie", "show"}
        ]

    def section_items(self, section_key: str, library: str) -> list[PlexMedia]:
        root = self.get_xml(f"/library/sections/{section_key}/all")
        items: list[PlexMedia] = []
        for node in root:
            if node.tag not in {"Video", "Directory"}:
                continue
            if node.attrib.get("type") in {"movie", "show"}:
                items.append(_media_from_element(node, library))
        return items

    def playlists(self) -> list[PlexMedia]:
        root = self.get_xml("/playlists", playlistType="video")
        return [
            _media_from_element(node)
            for node in root.findall("Playlist")
            if node.attrib.get("playlistType") == "video"
        ]

    def metadata(self, rating_key: int) -> PlexMedia | None:
        return self._first_media(self.get_xml(f"/library/metadata/{rating_key}"))

    def on_deck(self, show_rating_key: int) -> PlexMedia | None:
        root = self.get_xml(f"/library/metadata/{show_rating_key}", includeOnDeck=1)
        return self._first_media(root.findall("./Directory/OnDeck/Video"))

    def _first_media(
        self, nodes: ET.Element | Iterable[ET.Element]
    ) -> PlexMedia | None:
        if isinstance(nodes, ET.Element):
            iterable = nodes.iter()
        else:
            iterable = nodes
        for node in iterable:
            if node.tag in {"Video", "Directory", "Playlist"} and node.attrib.get(
                "ratingKey"
            ):
                return _media_from_element(node)
        return None

    def _redact(self, text: str) -> str:
        if not self._token:
            return text
        return text.replace(self._token, "<redacted>")
