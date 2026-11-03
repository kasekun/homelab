from __future__ import annotations

import pytest

from jplex.models import CatalogItem
from jplex.search import SelectionError, search_catalog, select_item


ITEMS = [
    CatalogItem(1, "movie", "Doom", 2005, "Movies", "uri://1"),
    CatalogItem(2, "movie", "Doomsday", 2008, "Movies", "uri://2"),
    CatalogItem(3, "show", "Final Space", 2018, "TV", "uri://3"),
    CatalogItem(4, "playlist", "Futurama Shuffle", None, None, "uri://4"),
    CatalogItem(5, "movie", "1917", 2019, "Movies", "uri://5"),
    CatalogItem(1917, "show", "Some Other Item", 2020, "TV", "uri://1917"),
]


def test_search_ranks_exact_before_prefix_and_fuzzy() -> None:
    results = search_catalog(ITEMS, "doom", limit=3)

    assert [result.item.rating_key for result in results[:2]] == [1, 2]
    assert results[0].reason == "exact"
    assert results[1].reason == "prefix"


def test_select_accepts_rating_key() -> None:
    assert select_item(ITEMS, "4").title == "Futurama Shuffle"


def test_select_allows_numeric_title_when_rating_key_is_filtered_out() -> None:
    assert select_item(ITEMS, "1917", item_type="movie").title == "1917"


def test_select_rejects_ambiguous_numeric_rating_key_and_title() -> None:
    with pytest.raises(SelectionError, match="matches both a rating key and a title"):
        select_item(ITEMS, "1917")


def test_select_rejects_ambiguous_prefix_even_with_limit_one() -> None:
    with pytest.raises(SelectionError) as raised:
        select_item(ITEMS, "doo", limit=1)

    assert "Multiple" in str(raised.value)
    assert len(raised.value.candidates) == 1


def test_select_rejects_weak_fuzzy_match() -> None:
    with pytest.raises(SelectionError):
        select_item(ITEMS, "zzzzzz")


def test_select_reports_no_matches_without_empty_candidate_hint() -> None:
    with pytest.raises(SelectionError, match="No matches for 'doom'"):
        select_item(ITEMS, "doom", item_type="playlist")
