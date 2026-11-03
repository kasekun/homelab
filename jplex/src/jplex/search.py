from __future__ import annotations

import re

from rapidfuzz import fuzz

from .models import CatalogItem, ItemType, SearchResult


WORD_RE = re.compile(r"[a-z0-9]+")


class SelectionError(RuntimeError):
    def __init__(
        self, message: str, candidates: list[SearchResult] | None = None
    ) -> None:
        super().__init__(message)
        self.candidates = candidates or []


def normalize(text: str) -> str:
    return " ".join(WORD_RE.findall(text.casefold()))


def search_catalog(
    items: list[CatalogItem],
    query: str,
    item_type: ItemType | None = None,
    year: int | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    needle = normalize(query)
    results: list[SearchResult] = []
    for item in items:
        if item_type and item.type != item_type:
            continue
        if year is not None and item.year != year:
            continue
        title = normalize(item.title)
        score, reason = score_title(needle, title)
        if score >= 55:
            results.append(SearchResult(item, score, reason))
    results.sort(
        key=lambda result: (
            -result.score,
            result.item.title,
            result.item.year or 0,
            result.item.rating_key,
        )
    )
    return results[:limit]


def score_title(needle: str, title: str) -> tuple[float, str]:
    if needle == title:
        return 100, "exact"
    if title.startswith(needle):
        return 92, "prefix"
    score = float(fuzz.WRatio(needle, title))
    return score, "fuzzy"


def select_item(
    items: list[CatalogItem],
    target: str,
    item_type: ItemType | None = None,
    year: int | None = None,
    limit: int = 10,
) -> CatalogItem:
    candidates = search_catalog(items, target, item_type, year, limit=max(limit, 10))

    if target.isdigit():
        rating_key_match = find_rating_key(items, int(target), item_type, year)
        title_matches = [
            result for result in candidates if result.reason in {"exact", "prefix"}
        ]
        if rating_key_match and not title_matches:
            return rating_key_match
        if rating_key_match and all(
            result.item == rating_key_match for result in title_matches
        ):
            return rating_key_match
        if rating_key_match and title_matches:
            raise SelectionError(
                "Numeric target matches both a rating key and a title. Use --type or --year to narrow results.",
                [SearchResult(rating_key_match, 100, "ratingKey"), *title_matches][
                    :limit
                ],
            )

    if not candidates:
        raise SelectionError(f"No matches for {target!r}.")

    exact = [result for result in candidates if result.reason == "exact"]
    if len(exact) == 1:
        return exact[0].item
    if len(exact) > 1:
        raise SelectionError(
            "Multiple exact matches. Use the rating key.", exact[:limit]
        )

    prefix = [result for result in candidates if result.reason == "prefix"]
    if len(prefix) == 1:
        return prefix[0].item
    if len(prefix) > 1:
        raise SelectionError(
            "Multiple prefix matches. Use the rating key.", prefix[:limit]
        )

    raise SelectionError(
        "No safe automatic match. Use one of these rating keys.", candidates[:limit]
    )


def find_rating_key(
    items: list[CatalogItem],
    rating_key: int,
    item_type: ItemType | None,
    year: int | None,
) -> CatalogItem | None:
    for item in items:
        if item.rating_key != rating_key:
            continue
        if item_type is not None and item.type != item_type:
            continue
        if year is not None and item.year != year:
            continue
        return item
    return None
