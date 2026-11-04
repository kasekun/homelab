from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


ItemType = Literal["movie", "show", "playlist"]
PlayMode = Literal["restart", "resume", "shuffle"]


@dataclass(frozen=True)
class CatalogItem:
    rating_key: int
    type: ItemType
    title: str
    year: int | None
    library: str | None
    uri: str
    key: str | None = None
    edition: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CatalogItem":
        return cls(
            rating_key=int(data["ratingKey"]),
            type=data["type"],
            title=data["title"],
            year=data.get("year"),
            library=data.get("library"),
            uri=data["uri"],
            key=data.get("key"),
            edition=data.get("edition"),
        )

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["ratingKey"] = data.pop("rating_key")
        return {key: value for key, value in data.items() if value is not None}


@dataclass(frozen=True)
class SearchResult:
    item: CatalogItem
    score: float
    reason: str


@dataclass(frozen=True)
class PlaybackPlan:
    item: CatalogItem
    mode: PlayMode
    uri: str
    url: str
    offset: int = 0
    key: str | None = None
    shuffle: bool = False
    target_rating_key: int | None = None
    target_title: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "ratingKey": self.item.rating_key,
            "type": self.item.type,
            "title": self.item.title,
            "mode": self.mode,
            "targetRatingKey": self.target_rating_key or self.item.rating_key,
            "targetTitle": self.target_title or self.item.title,
            "uri": self.uri,
            "key": self.key,
            "offset": self.offset,
            "shuffle": self.shuffle,
            "url": self.url,
        }
