# jplex

`jplex` is a local CLI for Plex search, playback planning, and NVIDIA SHIELD launch.

It keeps Plex API/catalog/search/planning logic testable and isolates ADB calls in one launcher module.

## Requirements

- A Plex server reachable from the machine running `jplex`.
- A Plex token with access to that server (see instructions below)
- An NVIDIA SHIELD TV with Plex installed (other Android TV devices may work, but are untested)
- `adb` installed on the machine running `jplex`, or `JPLEX__ADB_BIN` set to the `adb` executable.
- Network access from the local machine to the SHIELD's ADB endpoint, usually `<shield-ip>:5555`.
- Android Developer Options enabled on the SHIELD.
- Network debugging enabled on the SHIELD.
- Debug access approved on the SHIELD when `adb` first connects.

## Setup

```bash
cd jplex
uv sync  # don't have uv? https://docs.astral.sh/uv/getting-started/installation/
cp .env-example .env
```

Fill in `.env`:

```dotenv
JPLEX__PLEX_URL="http://127.0.0.1:32400"
JPLEX__PLEX_TOKEN=""
JPLEX__ADB_DEVICE_ADDRESS="192.168.1.126:5555"
# JPLEX__ADB_BIN="adb"
JPLEX__ROUTE_SETTLE_MS=900
JPLEX__SHOW__AUDIO_PREVIEW_GRACE_MS=1800
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
uv run jplex plan 49444 --shuffle --json
uv run jplex play 49444 --shuffle --dry-run
uv run jplex play "dune" --from-start # will search for and play dune from start of film
```

`TARGET` can be a rating key or a search query. Query-based commands only auto-select exact matches or a single confident prefix match; fuzzy matches print candidates and fail.

Omitting `--mode` resumes movies and shows, and starts playlists at the first item. Use `--from-start` for `--mode restart`, or `--shuffle` for `--mode shuffle`; mode selectors are mutually exclusive.

## Mechanism

when issuing a `jplex play` the process is as follows:

1. Launch plex if it is closed / not foreground
2. Navigate to home (leaving any details page or playing media)
3. Navigate to the details page for your chosen media
4. Launch chosen media

## Configuration

  - `JPLEX__SHOW__AUDIO_PREVIEW_GRACE_MS` dictates the time jplex will allow for the audio preview on tv show details page to play (step 3 above). Jplex waits for this to play, cancels it, before issuing the launch media command (without the cancel, "resume" timestamp doesn't work).

  - `JPLEX__ROUTE_SETTLE_MS` The amount of time between jplex steps

  - `JPLEX__PLEX_URL` set to `http://127.0.0.1:32400` if running jplex from the same machine as your plex server, otherwise set to `http://<plex server ip>:32400`


## Tests

```bash
uv run pytest
```
