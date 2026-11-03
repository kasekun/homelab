# jplex

`jplex` is a local CLI for Plex search, playback planning, and NVIDIA SHIELD launch.

It keeps Plex API/catalog/search/planning logic testable and isolates ADB calls in one launcher module.

## Setup

```bash
cd jplex
uv sync
cp .env-example .env
```

Fill in `.env`:

```dotenv
JPLEX_PLEX_URL="http://127.0.0.1:32400"
JPLEX_PLEX_TOKEN=""
JPLEX_ADB_DEVICE="192.168.1.126:5555"
# JPLEX_ADB_BIN="adb"
```

To get your `PLEX_TOKEN`

1. navigate to `app.plex.tv` in your browser
2. open browser console, and allow command pasting (run the command `allow pasting`)
3. run the command `window.localStorage.getItem('myPlexAccessToken')`, the result is your longlived plex token. Copy it without the enclosing quotes.


## Usage

```bash
uv run jplex adb check
uv run jplex cache refresh
uv run jplex search "doom"
uv run jplex key "Futurama" --type playlist --limit 1
uv run jplex plan 49444 --mode shuffle --json
uv run jplex play 49444 --mode shuffle --dry-run
```

`TARGET` can be a rating key or a search query. Query-based commands only auto-select exact matches or a single confident prefix match; fuzzy matches print candidates and fail.

## Tests

```bash
uv run pytest
```
