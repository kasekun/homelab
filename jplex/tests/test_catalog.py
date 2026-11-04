from __future__ import annotations

from jplex.catalog import Catalog, load_catalog, write_catalog
from jplex.models import CatalogItem


def item() -> CatalogItem:
    return CatalogItem(
        rating_key=1,
        type="movie",
        title="Movie",
        year=2024,
        library="Movies",
        uri="server://machine/com.plexapp.plugins.library/library/metadata/1",
    )


def test_write_catalog_round_trips_without_leaving_temp_file(tmp_path) -> None:
    path = tmp_path / "catalog.json"
    catalog = Catalog(
        machine_id="machine",
        metadata={"machineId": "machine", "counts": {"movie": 1}},
        items=[item()],
    )

    write_catalog(path, catalog)

    loaded = load_catalog(path)
    assert loaded.machine_id == "machine"
    assert loaded.items == [item()]
    assert not list(tmp_path.glob(".catalog.json.*.tmp"))
