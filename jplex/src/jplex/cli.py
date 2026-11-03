from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from .adb_launcher import ADBError, ADBLauncher
from .catalog import Catalog, load_catalog, refresh_catalog
from .config import Settings, load_settings
from .models import ItemType, PlayMode
from .planner import PlanningError, plan_playback
from .plex_api import PlexAPIError, PlexClient
from .search import SelectionError, search_catalog, select_item


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def settings_options(command: Any) -> Any:
    options = [
        click.option(
            "--refresh",
            is_flag=True,
            help="Refresh the catalog before resolving items.",
        ),
        click.option(
            "--env-file",
            type=click.Path(path_type=Path),
            help="Load JPLEX_* config from this file.",
        ),
        click.option(
            "--cache-path", type=click.Path(path_type=Path), help="Catalog cache path."
        ),
        click.option("--adb-bin", help="ADB executable path."),
        click.option("--adb-device", help="ADB serial or host[:port]."),
        click.option(
            "--token", "plex_token", help="Plex token. Prefer JPLEX_PLEX_TOKEN."
        ),
        click.option("--plex-url", help="Plex server URL."),
    ]
    for option in options:
        command = option(command)
    return command


@click.group(context_settings=CONTEXT_SETTINGS)
@settings_options
@click.pass_context
def main(
    ctx: click.Context, env_file: Path | None, refresh: bool, **overrides: object
) -> None:
    """Search Plex, plan watch URLs, and launch Plex on the SHIELD."""
    ctx.obj = {
        "settings": load_settings(env_file=env_file, **overrides),
        "refresh": refresh,
    }


@main.command()
@click.argument("query")
@click.option("--type", "item_type", type=click.Choice(["movie", "show", "playlist"]))
@click.option("--year", type=int)
@click.option("--limit", type=int, default=10, show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    item_type: ItemType | None,
    year: int | None,
    limit: int,
    as_json: bool,
) -> None:
    """Search the cached Plex catalog."""
    catalog = get_catalog(ctx)
    results = search_catalog(catalog.items, query, item_type, year, limit)
    if as_json:
        click.echo(json.dumps([result_to_json(result) for result in results], indent=2))
        return
    print_results(results)


@main.command()
@click.argument("target")
@click.option("--type", "item_type", type=click.Choice(["movie", "show", "playlist"]))
@click.option("--year", type=int)
@click.option("--limit", type=int, default=1, show_default=True)
@click.pass_context
def key(
    ctx: click.Context,
    target: str,
    item_type: ItemType | None,
    year: int | None,
    limit: int,
) -> None:
    """Print the rating key for one safely resolved item."""
    item = resolve_or_exit(get_catalog(ctx), target, item_type, year, limit)
    click.echo(item.rating_key)


@main.command("plan")
@click.argument("target")
@click.option("--type", "item_type", type=click.Choice(["movie", "show", "playlist"]))
@click.option("--year", type=int)
@click.option(
    "--mode",
    type=click.Choice(["start", "resume", "next", "shuffle"]),
    default="start",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def plan_cmd(
    ctx: click.Context,
    target: str,
    item_type: ItemType | None,
    year: int | None,
    mode: PlayMode,
    as_json: bool,
) -> None:
    """Build the Plex watch URL for a target without launching it."""
    catalog = get_catalog(ctx)
    item = resolve_or_exit(catalog, target, item_type, year, 10)
    plan = build_plan_or_exit(ctx, catalog, item, mode)
    if as_json:
        click.echo(json.dumps(plan.to_json(), indent=2))
        return
    click.echo(
        f"{plan.item.title} [{plan.item.type} {plan.item.rating_key}] {plan.mode} offset={plan.offset} shuffle={plan.shuffle}"
    )
    if (
        plan.target_rating_key is not None
        and plan.target_rating_key != plan.item.rating_key
    ):
        click.echo(f"target={plan.target_title} [{plan.target_rating_key}]")
    click.echo(plan.url)


@main.command()
@click.argument("target")
@click.option("--type", "item_type", type=click.Choice(["movie", "show", "playlist"]))
@click.option("--year", type=int)
@click.option(
    "--mode",
    type=click.Choice(["start", "resume", "next", "shuffle"]),
    default="start",
    show_default=True,
)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def play(
    ctx: click.Context,
    target: str,
    item_type: ItemType | None,
    year: int | None,
    mode: PlayMode,
    dry_run: bool,
) -> None:
    """Plan and launch playback on the configured SHIELD."""
    catalog = get_catalog(ctx)
    item = resolve_or_exit(catalog, target, item_type, year, 10)
    plan = build_plan_or_exit(ctx, catalog, item, mode)
    launcher = ADBLauncher(current_settings(ctx))
    if dry_run:
        click.echo(json.dumps(plan.to_json(), indent=2))
        click.echo("\nADB commands:")
        for command in launcher.dry_run_commands(plan.url):
            click.echo(command.display())
        return
    try:
        launcher.launch(plan.url)
    except ADBError as error:
        raise click.ClickException(str(error)) from error


@main.group()
def adb() -> None:
    """ADB diagnostics."""


@adb.command("check")
@click.pass_context
def adb_check(ctx: click.Context) -> None:
    """Check ADB and the configured SHIELD connection."""
    try:
        click.echo(ADBLauncher(current_settings(ctx)).check())
    except ADBError as error:
        raise click.ClickException(str(error)) from error


@main.group()
def cache() -> None:
    """Catalog cache commands."""


@cache.command("refresh")
@click.pass_context
def cache_refresh(ctx: click.Context) -> None:
    """Refresh the Plex catalog cache."""
    settings = current_settings(ctx)
    try:
        catalog = refresh_catalog(make_client(settings), settings.cache_path)
    except (OSError, PlexAPIError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"wrote {settings.cache_path} ({len(catalog.items)} items)")


def current_settings(ctx: click.Context) -> Settings:
    return ctx.find_root().obj["settings"]


def current_refresh(ctx: click.Context) -> bool:
    return bool(ctx.find_root().obj["refresh"])


def make_client(settings: Settings) -> PlexClient:
    return PlexClient(settings.plex_url, settings.plex_token)


def get_catalog(ctx: click.Context) -> Catalog:
    settings = current_settings(ctx)
    try:
        if current_refresh(ctx) or not settings.cache_path.exists():
            return refresh_catalog(make_client(settings), settings.cache_path)
        return load_catalog(settings.cache_path)
    except (OSError, PlexAPIError) as error:
        raise click.ClickException(str(error)) from error


def resolve_or_exit(
    catalog: Catalog,
    target: str,
    item_type: ItemType | None,
    year: int | None,
    limit: int,
):
    try:
        return select_item(catalog.items, target, item_type, year, limit)
    except SelectionError as error:
        for result in error.candidates:
            item = result.item
            year_text = item.year or ""
            click.echo(
                f"{item.rating_key}\t{item.type}\t{item.title}\t{year_text}\t{result.reason} {result.score:.0f}",
                err=True,
            )
        raise click.ClickException(str(error)) from error


def build_plan_or_exit(ctx: click.Context, catalog: Catalog, item: Any, mode: PlayMode):
    settings = current_settings(ctx)
    needs_api = mode in {"resume", "next"}
    client = make_client(settings) if needs_api else None
    try:
        return plan_playback(item, mode, client, catalog.machine_id)
    except (PlanningError, PlexAPIError) as error:
        raise click.ClickException(str(error)) from error


def result_to_json(result: Any) -> dict[str, Any]:
    item = result.item
    return {
        "ratingKey": item.rating_key,
        "type": item.type,
        "title": item.title,
        "year": item.year,
        "library": item.library,
        "score": result.score,
        "reason": result.reason,
    }


def print_results(results: list[Any]) -> None:
    for result in results:
        item = result.item
        year = item.year or ""
        library = item.library or ""
        click.echo(
            f"{item.rating_key}\t{item.type}\t{item.title}\t{year}\t{library}\t{result.reason} {result.score:.0f}"
        )
